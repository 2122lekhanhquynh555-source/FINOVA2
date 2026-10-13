#!/usr/bin/env python3
"""Download landmark photos from Wikimedia Commons into static/img/scenes/ (run at build time).

* Searches Commons for each landmark, keeps only openly licensed landscape JPEGs, saves 1.jpg ... 8.jpg
* Writes credits.json (title, author, licence, link) shown in the site footer
* NEVER fails the build: if the network or a photo is unavailable the site falls back to illustrations
Environment: WIKI_API overrides the API endpoint (used by the tests)."""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

API = os.getenv("WIKI_API", "https://commons.wikimedia.org/w/api.php")
UA = "FINOVA-education-project/1.0 (student web app; downloads a few openly licensed photos at build time)"
OUT = Path(os.getenv("SCENES_DIR", Path(__file__).resolve().parent.parent / "static" / "img" / "scenes"))
SLOTS = ["Ha Long Bay Vietnam sunset", "Hoan Kiem Lake Hanoi", "Sa Pa rice terraces Vietnam", "Hoi An ancient town Vietnam",
         "Ho Chi Minh City skyline Saigon river", "Trang An Ninh Binh Vietnam", "One Pillar Pagoda Hanoi", "Phu Quoc island beach Vietnam"]
OPEN = re.compile(r"(CC[ -]?(BY|0)|Public domain|PD)", re.I)


def fetch(url, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout) as r:
        return r.read()


def candidates(query):
    params = {"action": "query", "generator": "search", "gsrsearch": query, "gsrnamespace": "6", "gsrlimit": "20", "prop": "imageinfo",
              "iiprop": "url|size|mime|extmetadata", "iiurlwidth": "1600", "format": "json"}
    data = json.loads(fetch(API + "?" + urllib.parse.urlencode(params)))
    pages = sorted((data.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName") or {}).get("value", "")
        if ii.get("mime") == "image/jpeg" and ii.get("width", 0) >= 1400 and ii["width"] >= 1.25 * ii.get("height", 1) and OPEN.search(lic):
            artist = re.sub(r"<[^>]+>", "", unescape((meta.get("Artist") or {}).get("value", "Wikimedia Commons contributor"))).strip()[:80]
            yield {"title": p.get("title", "").replace("File:", ""), "url": ii.get("thumburl") or ii["url"], "page": ii.get("descriptionshorturl") or ii.get("descriptionurl", ""),
                   "artist": artist or "Wikimedia Commons contributor", "license": lic}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    credits = {}
    cf = OUT / "credits.json"
    if cf.exists():
        try:
            credits = json.loads(cf.read_text())
        except ValueError:
            credits = {}
    ok = 0
    for i, q in enumerate(SLOTS, 1):
        dest = OUT / f"{i}.jpg"
        if dest.exists() and dest.stat().st_size > 20000:
            ok += 1
            continue
        try:
            for c in candidates(q):
                try:
                    raw = fetch(c["url"], 60)
                except Exception:
                    continue
                if raw[:3] == b"\xff\xd8\xff" and len(raw) > 20000:
                    dest.write_bytes(raw)
                    credits[str(i)] = {k: c[k] for k in ("title", "page", "artist", "license")}
                    ok += 1
                    print(f"[photos] {i}.jpg <- {c['title']}")
                    break
            else:
                print(f"[photos] no suitable photo for: {q}")
        except Exception as e:                      # offline, API error, anything
            print(f"[photos] skipped '{q}': {type(e).__name__}")
    cf.write_text(json.dumps(credits, ensure_ascii=False, indent=1))
    print(f"[photos] {ok}/{len(SLOTS)} photos available")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:                          # never break the deploy
        print("[photos] failed:", type(e).__name__)
        sys.exit(0)
