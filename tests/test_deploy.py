"""Deployment safety: the Blueprint must only create FREE resources, and the photo downloader must never break a build."""
import io, json, os, re, subprocess, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


class BlueprintIsFree(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / "render.yaml").read_text()
        self.cfg = yaml.safe_load(self.text)

    def test_only_one_free_web_service(self):
        self.assertEqual(set(self.cfg) - {"services"}, set(), "no databases / keyvalue / envVarGroups / previews / paid top-level resources")
        svcs = self.cfg["services"]
        self.assertEqual(len(svcs), 1)
        s = svcs[0]
        self.assertEqual(s["type"], "web"); self.assertEqual(s["plan"], "free")
        for forbidden in ("disk", "disks", "numInstances", "scaling", "autoscaling", "maxShutdownDelaySeconds"):
            self.assertNotIn(forbidden, s, forbidden)

    def test_no_paid_keywords_anywhere(self):
        code = "\n".join(re.sub(r"\s#.*$", "", l) for l in self.text.splitlines() if not l.strip().startswith("#"))
        for word in ("starter", "standard", "pro", "plus", "pserv", "worker", "cron", "redis", "keyvalue", "postgres", "databases", "disk:"):
            self.assertIsNone(re.search(rf"\b{re.escape(word)}\b", code), word)

    def test_start_and_build_commands(self):
        s = self.cfg["services"][0]
        self.assertIn("gunicorn app:app", s["startCommand"]); self.assertIn("$PORT", s["startCommand"])
        self.assertIn("fetch_photos.py", s["buildCommand"]); self.assertIn("|| true", s["buildCommand"])      # photo download can never fail the deploy
        keys = {e["key"]: e for e in s["envVars"]}
        self.assertTrue(keys["SECRET_KEY"].get("generateValue")); self.assertTrue(keys["GEMINI_API_KEY"].get("sync") is False)
        self.assertNotIn("value", keys["GEMINI_API_KEY"])                                                       # no secret committed

    def test_requirements_complete(self):
        req = (ROOT / "requirements.txt").read_text().lower()
        for pkg in ("flask", "gunicorn", "openpyxl", "requests"):
            self.assertIn(pkg, req)


class MockCommons(BaseHTTPRequestHandler):
    jpeg = None
    def log_message(self, *a): pass
    def do_GET(self):
        u = urlparse(self.path)
        if u.path.endswith("api.php"):
            q = parse_qs(u.query)["gsrsearch"][0]
            base = f"http://127.0.0.1:{self.server.server_address[1]}"
            def page(i, mime, w, h, lic, path):
                return {"index": i, "title": f"File:{q}-{i}.jpg", "imageinfo": [{"mime": mime, "width": w, "height": h, "thumburl": f"{base}/{path}", "url": f"{base}/{path}",
                        "descriptionshorturl": f"{base}/page{i}", "extmetadata": {"LicenseShortName": {"value": lic}, "Artist": {"value": "<a href='x'>Jane &amp; Co</a>"}}}]}
            pages = {"1": page(1, "image/png", 2000, 1000, "CC BY-SA 4.0", "good.jpg"), "2": page(2, "image/jpeg", 2000, 2000, "CC BY 4.0", "good.jpg"),
                     "3": page(3, "image/jpeg", 2000, 1200, "Fair use", "good.jpg"), "4": page(4, "image/jpeg", 2000, 1200, "CC BY-SA 4.0", "notjpeg.jpg"),
                     "5": page(5, "image/jpeg", 2000, 1200, "CC BY-SA 4.0", "good.jpg")}
            body = json.dumps({"query": {"pages": pages}}).encode(); ct = "application/json"
        elif u.path.endswith("notjpeg.jpg"):
            body, ct = b"<html>blocked</html>" * 2000, "text/html"
        else:
            body, ct = MockCommons.jpeg, "image/jpeg"
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)


class PhotoDownloader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        buf = io.BytesIO(); Image.effect_noise((1600, 900), 80).convert("RGB").save(buf, "JPEG", quality=90); MockCommons.jpeg = buf.getvalue()
        cls.srv = HTTPServer(("127.0.0.1", 0), MockCommons); threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    def run_script(self, api, out):
        return subprocess.run([sys.executable, str(ROOT / "tools" / "fetch_photos.py")], env={**os.environ, "WIKI_API": api, "SCENES_DIR": out}, capture_output=True, text=True, timeout=120)

    def test_downloads_filters_and_credits(self):
        out = tempfile.mkdtemp(); r = self.run_script(f"http://127.0.0.1:{self.srv.server_address[1]}/w/api.php", out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        files = sorted(p.name for p in Path(out).glob("*.jpg")); self.assertEqual(files, [f"{i}.jpg" for i in range(1, 9)])
        for f in Path(out).glob("*.jpg"): self.assertEqual(f.read_bytes()[:3], b"\xff\xd8\xff")
        cred = json.loads((Path(out) / "credits.json").read_text())
        self.assertEqual(len(cred), 8); c = cred["1"]
        self.assertTrue(c["title"].endswith("-5.jpg"), c)               # png / square / non-open licence / fake jpeg were all skipped
        self.assertEqual(c["artist"], "Jane & Co"); self.assertIn("CC BY", c["license"]); self.assertTrue(c["page"].startswith("http"))
        before = (Path(out) / "1.jpg").stat().st_mtime_ns; self.run_script(f"http://127.0.0.1:{self.srv.server_address[1]}/w/api.php", out)
        self.assertEqual((Path(out) / "1.jpg").stat().st_mtime_ns, before)   # idempotent

    def test_offline_never_fails_the_build(self):
        out = tempfile.mkdtemp(); r = self.run_script("http://127.0.0.1:9/w/api.php", out)
        self.assertEqual(r.returncode, 0); self.assertEqual(list(Path(out).glob("*.jpg")), []); self.assertIn("skipped", r.stdout)


if __name__ == "__main__":
    unittest.main()
