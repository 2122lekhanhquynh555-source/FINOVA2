"""FINOVA — Flask backend (serves the SPA in /static and the JSON API)."""
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import sqlite3
import time
from email.message import EmailMessage
from functools import wraps
from io import BytesIO
from pathlib import Path

from flask import Flask, g, jsonify, request, send_file, send_from_directory, session
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

import ai
import engine
import narrative
import verify

try:  # optional: load .env locally (Render uses dashboard env vars)
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE = Path(__file__).parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE / "instance"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "uploads").mkdir(exist_ok=True)
DB_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "finova.db"))


def _secret():
    """Stable secret shared by all gunicorn workers (env var, else a file created atomically once)."""
    if os.getenv("SECRET_KEY"):
        return os.getenv("SECRET_KEY")
    f = DATA_DIR / "secret.key"
    try:
        fd = os.open(f, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)   # only one worker wins the race
        with os.fdopen(fd, "w") as fh:
            fh.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    for _ in range(50):                                                 # loser waits for the winner's write
        key = f.read_text().strip()
        if key:
            return key
        time.sleep(0.05)
    return secrets.token_hex(32)


app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = _secret()
SECURE = bool(os.getenv("RENDER") or os.getenv("FORCE_SECURE_COOKIES"))
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=SECURE,
                  MAX_CONTENT_LENGTH=6 * 1024 * 1024, PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 14)
if SECURE:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

FAQ = json.loads((BASE / "data" / "faq.json").read_text(encoding="utf-8"))
KB = ai.KB(FAQ, BASE / "data" / "docs.md")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EVENTS = {"finance_saved", "results_viewed", "whatif_run", "goals_analyzed", "plan_saved", "exported", "ai_parse_used", "excel_imported"}
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, pw TEXT, age INTEGER, gender TEXT,
  country TEXT, province TEXT, phone TEXT, occupation TEXT, created REAL);
CREATE TABLE IF NOT EXISTS finance(user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, data TEXT, updated REAL);
CREATE TABLE IF NOT EXISTS plans(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, name TEXT, data TEXT, created REAL, updated REAL);
CREATE TABLE IF NOT EXISTS ratings(user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, accuracy INTEGER, groundedness INTEGER,
  usability INTEGER, processing INTEGER, avg REAL, comment TEXT, flagged INTEGER, updated REAL);
CREATE TABLE IF NOT EXISTS metrics(id INTEGER PRIMARY KEY, name TEXT, ms REAL, created REAL);
CREATE TABLE IF NOT EXISTS llm_log(id INTEGER PRIMARY KEY, task TEXT, source TEXT, error TEXT, ms REAL, g_ok INTEGER, g_checked INTEGER, rejected INTEGER, created REAL);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, created REAL);
CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, k TEXT, created REAL);
CREATE TABLE IF NOT EXISTS resets(user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, code TEXT, expires REAL, tries INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, type TEXT, subject TEXT, description TEXT,
  email TEXT, attachment TEXT, status TEXT DEFAULT 'open', note TEXT, created REAL, updated REAL);
CREATE TABLE IF NOT EXISTS goal_drafts(user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, data TEXT, updated REAL);
CREATE INDEX IF NOT EXISTS i_plans ON plans(user_id); CREATE INDEX IF NOT EXISTS i_att ON attempts(k, created);
CREATE INDEX IF NOT EXISTS i_ev ON events(user_id, name); CREATE INDEX IF NOT EXISTS i_tk ON tickets(user_id);
"""


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()


with sqlite3.connect(DB_PATH, timeout=30) as _c:
    _c.execute("PRAGMA journal_mode=WAL")
    _c.executescript(SCHEMA)


def err(msg, code=400, **extra):
    return jsonify({"error": msg, **extra}), code


def ip():
    return request.remote_addr or "?"


def throttle(key, limit, window, record=False):
    """True when `key` has reached `limit` events in the last `window` seconds (shared by all workers via SQLite)."""
    now = time.time()
    db().execute("DELETE FROM attempts WHERE created<?", (now - 3600,))
    n = db().execute("SELECT COUNT(*) c FROM attempts WHERE k=? AND created>?", (key, now - window)).fetchone()["c"]
    if record:
        db().execute("INSERT INTO attempts(k,created) VALUES(?,?)", (key, now))
        db().commit()
    return n >= limit


def too_many():
    return err("Too many attempts. Please wait a few minutes and try again.", 429)


# ------------------------------------------------------------ security
@app.before_request
def csrf_guard():
    if request.method in ("POST", "PUT", "DELETE") and request.path.startswith("/api/"):
        tok = session.get("csrf")
        if not tok or not hmac.compare_digest(tok, request.headers.get("X-CSRF-Token", "")):
            return err("Your session expired. Please refresh the page.", 403)


@app.after_request
def headers(r):
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    r.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    r.headers["Content-Security-Policy"] = ("default-src 'self'; script-src 'self' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                                            "font-src https://fonts.gstatic.com; img-src 'self' data: https://commons.wikimedia.org https://upload.wikimedia.org; "
                                            "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
    if SECURE:
        r.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.path.startswith("/api/"):
        r.headers["Cache-Control"] = "no-store"
    return r


@app.errorhandler(Exception)
def on_error(e):
    if isinstance(e, HTTPException):
        msg = {413: "The upload is too large (6 MB maximum).", 404: "Not found.", 405: "Method not allowed."}.get(e.code, e.description)
        return (jsonify({"error": msg}), e.code) if request.path.startswith("/api/") else (e.get_response())
    app.logger.exception("Unhandled error")
    return err("Something went wrong on the server. Please try again.", 500)


def login_required(fn):
    @wraps(fn)
    def w(*a, **k):
        if not session.get("uid") or not me():
            return err("Please log in first.", 401)
        return fn(*a, **k)
    return w


def is_admin(u):
    return bool(u) and u["email"] in {x.strip().lower() for x in os.getenv("ADMIN_EMAILS", "").split(",") if x.strip()}


def admin_required(fn):
    @wraps(fn)
    @login_required
    def w(*a, **k):
        return fn(*a, **k) if is_admin(me()) else err("Administrator access required.", 403)
    return w


def public_user(r):
    d = {k: r[k] for k in ("id", "name", "email", "age", "gender", "country", "province", "phone", "occupation")}
    d["is_admin"] = is_admin(r)
    return d


def me():
    if "me" not in g:
        g.me = db().execute("SELECT * FROM users WHERE id=?", (session.get("uid"),)).fetchone()
    return g.me


def new_session(uid=None):
    session.clear()
    session.permanent = True
    session["csrf"] = secrets.token_urlsafe(32)
    if uid:
        session["uid"] = uid
    g.pop("me", None)


def pw_ok(pw):
    return len(pw) >= 8 and re.search(r"[A-Za-z]", pw) and re.search(r"\d", pw)


def metric(name, ms):
    db().execute("INSERT INTO metrics(name,ms,created) VALUES(?,?,?)", (name, ms, time.time()))
    db().commit()


def track(name):
    db().execute("INSERT INTO events(user_id,name,created) VALUES(?,?,?)", (session["uid"], name, time.time()))
    db().commit()


def log_llm(task, res):
    gr = res.get("grounded") or {}
    db().execute("INSERT INTO llm_log(task,source,error,ms,g_ok,g_checked,rejected,created) VALUES(?,?,?,?,?,?,?,?)",
                 (task, res.get("source"), (res.get("error") or {}).get("code"), res.get("ms", 0), gr.get("ok", 0), gr.get("checked", 0),
                  len(res.get("rejected") or []), time.time()))
    db().commit()


def load_finance():
    r = db().execute("SELECT data FROM finance WHERE user_id=?", (session["uid"],)).fetchone()
    return json.loads(r["data"]) if r else None


def need_finance():
    f = load_finance()
    return f if f and (f.get("income") or f.get("expenses")) else None


NEED = "Please save your financial information first."


def send_mail(to, subject, body):
    host = os.getenv("SMTP_HOST")
    if not host:
        return False
    try:
        m = EmailMessage()
        m["From"], m["To"], m["Subject"] = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "no-reply@finova.local")), to, subject
        m.set_content(body)
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as s:
            if os.getenv("SMTP_TLS", "1") == "1":
                s.starttls()
            if os.getenv("SMTP_USER"):
                s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD", ""))
            s.send_message(m)
        return True
    except Exception:
        app.logger.warning("SMTP delivery failed")
        return False


# ------------------------------------------------------------------ pages
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/healthz")
def healthz():
    db().execute("SELECT 1")
    return "ok"


@app.get("/api/config")
def config():
    return jsonify({"ai_enabled": ai.configured(), "demo_reset": bool(os.getenv("ALLOW_DEMO_RESET")) and not os.getenv("SMTP_HOST")})


@app.get("/api/faq")
def faq():
    return jsonify(FAQ)


# ------------------------------------------------------------------- auth
@app.get("/api/me")
def whoami():
    if not session.get("csrf"):
        session["csrf"] = secrets.token_urlsafe(32)
    u = me() if session.get("uid") else None
    return jsonify({"user": public_user(u) if u else None, "csrf": session["csrf"]})


@app.post("/api/register")
def register():
    if throttle(f"reg:{ip()}", int(os.getenv("REGISTER_LIMIT", "10")), 3600, record=True):
        return too_many()
    d = request.get_json(silent=True) or {}
    name, email, pw = str(d.get("name", "")).strip()[:80], str(d.get("email", "")).strip().lower()[:120], str(d.get("password", ""))
    if len(name) < 2:
        return err("Please enter your full name.")
    if not EMAIL_RE.match(email):
        return err("Please enter a valid email address.")
    if not pw_ok(pw):
        return err("Password must be at least 8 characters and include letters and numbers.")
    if pw != d.get("confirm"):
        return err("Passwords do not match.")
    try:
        cur = db().execute("INSERT INTO users(name,email,pw,created) VALUES(?,?,?,?)", (name, email, generate_password_hash(pw), time.time()))
        db().commit()
    except sqlite3.IntegrityError:
        return err("An account with this email already exists.", 409)
    new_session(cur.lastrowid)
    return jsonify({"user": public_user(me()), "csrf": session["csrf"]})


@app.post("/api/login")
def login():
    d = request.get_json(silent=True) or {}
    email = str(d.get("email", "")).strip().lower()[:120]
    if throttle(f"login:{ip()}:{email}", 5, 600) or throttle(f"loginip:{ip()}", 40, 600):
        return too_many()
    r = db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not r or not check_password_hash(r["pw"], str(d.get("password", ""))):
        throttle(f"login:{ip()}:{email}", 99, 600, record=True)
        throttle(f"loginip:{ip()}", 99, 600, record=True)
        return err("Incorrect email or password.", 401)
    new_session(r["id"])
    return jsonify({"user": public_user(me()), "csrf": session["csrf"]})


@app.post("/api/logout")
def logout():
    new_session()
    return jsonify({"ok": True, "csrf": session["csrf"]})


@app.post("/api/forgot/verify")
def forgot_verify():
    email = str((request.get_json(silent=True) or {}).get("email", "")).strip().lower()[:120]
    if throttle(f"fg:{ip()}:{email}", 3, 600, record=True):
        return too_many()
    if not EMAIL_RE.match(email):
        return err("Please enter a valid email address.")
    r = db().execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    out = {"ok": True, "message": "If this email is registered, a 6-digit verification code has been sent."}
    if r:
        code = f"{secrets.randbelow(10 ** 6):06d}"
        db().execute("INSERT INTO resets(user_id,code,expires,tries) VALUES(?,?,?,0) ON CONFLICT(user_id) DO UPDATE SET code=excluded.code, expires=excluded.expires, tries=0",
                     (r["id"], hashlib.sha256(code.encode()).hexdigest(), time.time() + 600))
        db().commit()
        sent = send_mail(email, "Your FINOVA verification code", f"Your FINOVA password reset code is {code}. It expires in 10 minutes.\nIf you did not request it, ignore this email.")
        if not sent and os.getenv("ALLOW_DEMO_RESET") and not os.getenv("SMTP_HOST"):
            out["demo_code"] = code          # DEMO ONLY: no email service configured
    return jsonify(out)


@app.post("/api/forgot/reset")
def forgot_reset():
    d = request.get_json(silent=True) or {}
    email = str(d.get("email", "")).strip().lower()[:120]
    if throttle(f"fgr:{ip()}:{email}", 8, 600, record=True):
        return too_many()
    if not pw_ok(str(d.get("password", ""))):
        return err("Password must be at least 8 characters and include letters and numbers.")
    if d.get("password") != d.get("confirm"):
        return err("Passwords do not match.")
    u = db().execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    rs = db().execute("SELECT * FROM resets WHERE user_id=?", (u["id"],)).fetchone() if u else None
    if not rs or rs["expires"] < time.time() or rs["tries"] >= 5:
        return err("The code is invalid or expired. Please request a new one.", 403)
    db().execute("UPDATE resets SET tries=tries+1 WHERE user_id=?", (u["id"],))
    if not hmac.compare_digest(rs["code"], hashlib.sha256(str(d.get("code", "")).strip().encode()).hexdigest()):
        db().commit()
        return err("The code is invalid or expired. Please request a new one.", 403)
    db().execute("UPDATE users SET pw=? WHERE id=?", (generate_password_hash(d["password"]), u["id"]))
    db().execute("DELETE FROM resets WHERE user_id=?", (u["id"],))
    db().commit()
    return jsonify({"ok": True})


@app.put("/api/profile")
@login_required
def profile():
    d = request.get_json(silent=True) or {}
    name, email = str(d.get("name", "")).strip()[:80], str(d.get("email", "")).strip().lower()[:120]
    if len(name) < 2 or not EMAIL_RE.match(email):
        return err("Please enter a valid name and email.")
    try:
        age = int(d["age"]) if str(d.get("age", "")).strip() else None
    except ValueError:
        return err("Age must be a whole number.")
    if age is not None and not 1 <= age <= 120:
        return err("Age must be between 1 and 120.")
    gender = d.get("gender") if d.get("gender") in ("Male", "Female", "Other") else None
    try:
        db().execute("UPDATE users SET name=?,email=?,age=?,gender=?,country=?,province=?,phone=?,occupation=? WHERE id=?",
                     (name, email, age, gender, str(d.get("country", ""))[:80], str(d.get("province", ""))[:80],
                      re.sub(r"[^\d+\s-]", "", str(d.get("phone", "")))[:20], str(d.get("occupation", ""))[:80], session["uid"]))
        db().commit()
    except sqlite3.IntegrityError:
        return err("That email is already used by another account.", 409)
    g.pop("me", None)
    return jsonify({"user": public_user(me())})


@app.post("/api/password")
@login_required
def change_password():
    d = request.get_json(silent=True) or {}
    if throttle(f"pw:{session['uid']}", 5, 600, record=True):
        return too_many()
    if not check_password_hash(me()["pw"], str(d.get("old", ""))):
        return err("Your current password is incorrect.", 403)
    if not pw_ok(str(d.get("new", ""))):
        return err("New password must be at least 8 characters and include letters and numbers.")
    if d.get("new") != d.get("confirm"):
        return err("New passwords do not match.")
    db().execute("UPDATE users SET pw=? WHERE id=?", (generate_password_hash(d["new"]), session["uid"]))
    db().commit()
    return jsonify({"ok": True})


@app.post("/api/event")
@login_required
def event():
    n = str((request.get_json(silent=True) or {}).get("name", ""))
    if n in EVENTS:
        db().execute("INSERT INTO events(user_id,name,created) VALUES(?,?,?)", (session["uid"], n, time.time()))
        db().commit()
    return jsonify({"ok": True})


# --------------------------------------------------------------- finance
@app.route("/api/finance", methods=["GET", "PUT"])
@login_required
def finance():
    if request.method == "PUT":
        raw = request.get_json(silent=True) or {}
        issues = engine.validate_profile(raw)
        p = engine.clean_profile(raw)
        db().execute("INSERT INTO finance(user_id,data,updated) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET data=excluded.data, updated=excluded.updated",
                     (session["uid"], json.dumps(p), time.time()))
        db().commit()
        track("finance_saved")
        return jsonify({"finance": p, "issues": [i for i in issues if i["level"] != "info"]})
    return jsonify({"finance": load_finance()})


@app.get("/api/finance/template")
@login_required
def finance_template():
    return send_file(BytesIO(engine.template_xlsx()), as_attachment=True, download_name="finova_input_template.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.post("/api/finance/import")
@login_required
def finance_import():
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith(".xlsx"):
        return err("Please upload an .xlsx file.")
    try:
        parsed = engine.parse_xlsx(f.read())
    except ValueError as e:
        return err(str(e), 422)
    parsed["ai"] = {"status": "off", "remarks": [], "applied": {}}
    if ai.configured():                                  # Task 1: LLM review, Python-validated
        t = time.perf_counter()
        try:
            rv = ai.review_excel(parsed)
            parsed["ai"] = {"status": "ok", **rv}
            parsed["data"].update(rv["applied"])
            parsed["missing"] = [k for k in parsed["missing"] if k not in parsed["data"]]
            log_llm("parse_excel", {"source": "gemini", "ms": (time.perf_counter() - t) * 1000})
        except ai.AIError as e:
            parsed["ai"] = {"status": "error", "error": e.message, "remarks": [], "applied": {}}
            log_llm("parse_excel", {"source": "rules", "error": {"code": e.code}, "ms": (time.perf_counter() - t) * 1000})
    parsed["issues"] = [i for i in engine.validate_profile(parsed["data"]) if i["level"] != "info"]
    parsed.pop("rows", None)
    track("excel_imported")
    return jsonify(parsed)


@app.post("/api/ai/parse")
@login_required
def ai_parse():
    if throttle(f"ai:{session['uid']}", 20, 60, record=True):
        return too_many()
    t = time.perf_counter()
    try:
        r = ai.parse_text((request.get_json(silent=True) or {}).get("text"))
    except ai.AIError as e:
        log_llm("parse_text", {"source": "rules", "error": {"code": e.code}, "ms": (time.perf_counter() - t) * 1000})
        return err(e.message, 503 if e.code != "empty" else 400, ai_code=e.code)
    log_llm("parse_text", {"source": "gemini", "ms": (time.perf_counter() - t) * 1000})
    track("ai_parse_used")
    return jsonify(r)


# -------------------------------------------------------------- analysis
@app.get("/api/analysis")
@login_required
def analysis():
    f = need_finance()
    if not f:
        return err(NEED, 409)
    t = time.perf_counter()
    a = engine.analysis(f)
    ms = (time.perf_counter() - t) * 1000
    metric("analysis_engine", ms)
    a["narrative"], a["source"], a["engine_ms"] = narrative.analysis(a), "rules", ms
    track("results_viewed")
    return jsonify(a)


@app.post("/api/whatif")
@login_required
def whatif():
    f = need_finance()
    if not f:
        return err(NEED, 409)
    t = time.perf_counter()
    w = engine.whatif(f, (request.get_json(silent=True) or {}).get("adjustments"))
    metric("whatif_engine", (time.perf_counter() - t) * 1000)
    w["narrative"] = {"text": narrative.whatif(w, None)}
    track("whatif_run")
    return jsonify(w)


@app.post("/api/ai/explain")
@login_required
def ai_explain():
    d = request.get_json(silent=True) or {}
    kind, f = d.get("kind"), need_finance()
    if kind not in ai.KEYS or not f:
        return err("Unsupported request.")
    if throttle(f"ai:{session['uid']}", 20, 60, record=True):
        return too_many()
    if kind == "analysis":
        data = engine.analysis(f)
        fb = narrative.analysis(data)
    elif kind == "whatif":
        data = engine.whatif(f, d.get("adjustments"))
        fb = {"text": narrative.whatif(data, None)}
    else:
        data = engine.goals_analyze(f, d.get("goals"), d.get("chosen"), d.get("assumptions"))
        if "errors" in data:
            return err(" ".join(data["errors"]), 422)
        fb = narrative.goals(data) if kind == "goals" else {"text": narrative.secondary(data)}
    res = ai.explain(kind, data, fb)
    task = {"analysis": "explain_analysis", "whatif": "explain_whatif", "goals": "prioritize_goals", "secondary": "secondary_goal"}[kind]
    log_llm(task, res)
    if res["source"] in ("gemini", "partial"):
        metric("ai_generation", res["ms"])
    return jsonify(res)


# ----------------------------------------------------------------- goals
@app.get("/api/goals/defaults")
@login_required
def goal_defaults():
    f = need_finance()
    return jsonify({"goals": engine.default_goals(engine.clean_profile(f))}) if f else err(NEED, 409)


@app.route("/api/goals/draft", methods=["GET", "PUT"])
@login_required
def goals_draft():
    """Save / load the goal-input form of Savings & Investment (kept per account)."""
    if request.method == "PUT":
        d = request.get_json(silent=True) or {}
        goals = engine.clean_goals(d.get("goals"), keep_blank=True)
        if not goals:
            return err("Add at least one goal before saving.")
        chosen = d.get("chosen") if isinstance(d.get("chosen"), int) and 0 <= d.get("chosen") < len(goals) else None
        f = load_finance()
        notes = []
        if f:
            errs, warns = engine.validate_goals(engine.clean_profile(f), [g for g in goals if g["name"]])
            notes = errs + warns
        db().execute("INSERT INTO goal_drafts(user_id,data,updated) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET data=excluded.data, updated=excluded.updated",
                     (session["uid"], json.dumps({"goals": goals, "chosen": chosen}), time.time()))
        db().commit()
        return jsonify({"saved": True, "goals": goals, "notes": notes, "updated": time.time()})
    r = db().execute("SELECT data, updated FROM goal_drafts WHERE user_id=?", (session["uid"],)).fetchone()
    if not r:
        return jsonify({"goals": None})
    return jsonify({**json.loads(r["data"]), "updated": r["updated"]})


@app.post("/api/goals/analyze")
@login_required
def goals_analyze():
    f = need_finance()
    if not f:
        return err(NEED, 409)
    d = request.get_json(silent=True) or {}
    t = time.perf_counter()
    r = engine.goals_analyze(f, d.get("goals"), d.get("chosen"), d.get("assumptions"))
    metric("goals_engine", (time.perf_counter() - t) * 1000)
    if "errors" in r:
        return err(" ".join(r["errors"]), 422, errors=r["errors"], warnings=r["warnings"])
    r["narrative"] = narrative.goals(r)
    r["narrative"]["secondary"] = narrative.secondary(r)
    track("goals_analyzed")
    return jsonify(r)


def plan_summary(r):
    pl, pa = r["plan_baseline"], r["plan_assumed"]
    u = pa or pl
    return {"goal": pl["name"], "kind": pl["kind"], "target": pl["target"], "years": u["years"], "monthly_save": u["monthly_save"],
            "annual_return": u["annual_return"], "required_monthly": u["required_monthly"], "completion": u["completion"],
            "months": u["months_at_rate"], "projected": u["projected"], "hypothetical": bool(pa)}


def plan_row(r):
    return {"id": r["id"], "name": r["name"], "updated": r["updated"] or r["created"], **json.loads(r["data"])}


@app.route("/api/plans", methods=["GET", "POST"])
@login_required
def plans():
    if request.method == "POST":
        d = request.get_json(silent=True) or {}
        f = need_finance()
        if not f:
            return err(NEED, 409)
        r = engine.goals_analyze(f, d.get("goals"), d.get("chosen"), d.get("assumptions"))
        if "errors" in r:
            return err(" ".join(r["errors"]), 422)
        name = str(d.get("name", "")).strip()[:60] or "Untitled plan"
        n = db().execute("SELECT COUNT(*) c FROM plans WHERE user_id=?", (session["uid"],)).fetchone()["c"]
        if n >= 30:
            return err("You can keep up to 30 saved plans. Delete one first.", 400)
        now = time.time()
        cur = db().execute("INSERT INTO plans(user_id,name,data,created,updated) VALUES(?,?,?,?,?)",
                           (session["uid"], name, json.dumps({"goals": r["goals"], "chosen": d.get("chosen"), "assumptions": d.get("assumptions"), "summary": plan_summary(r)}), now, now))
        db().commit()
        track("plan_saved")
        saved = cur.lastrowid
    else:
        saved = None
    rows = db().execute("SELECT * FROM plans WHERE user_id=? ORDER BY id DESC", (session["uid"],)).fetchall()
    return jsonify({"plans": [plan_row(r) for r in rows], "saved_id": saved})


@app.route("/api/plans/<int:pid>", methods=["PUT", "DELETE"])
@login_required
def plan_item(pid):
    row = db().execute("SELECT * FROM plans WHERE id=? AND user_id=?", (pid, session["uid"])).fetchone()
    if not row:
        return err("Plan not found.", 404)
    if request.method == "DELETE":
        db().execute("DELETE FROM plans WHERE id=?", (pid,))
        db().commit()
        return jsonify({"ok": True})
    d = request.get_json(silent=True) or {}
    cur = json.loads(row["data"])
    name = str(d.get("name", row["name"])).strip()[:60] or row["name"]
    if "goals" in d:
        f = need_finance()
        if not f:
            return err(NEED, 409)
        r = engine.goals_analyze(f, d.get("goals"), d.get("chosen"), d.get("assumptions"))
        if "errors" in r:
            return err(" ".join(r["errors"]), 422)
        cur = {"goals": r["goals"], "chosen": d.get("chosen"), "assumptions": d.get("assumptions"), "summary": plan_summary(r)}
    db().execute("UPDATE plans SET name=?, data=?, updated=? WHERE id=?", (name, json.dumps(cur), time.time(), pid))
    db().commit()
    return jsonify({"ok": True, "id": pid})


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@app.get("/api/export/report")
@login_required
def export_report():
    f = need_finance()
    if not f:
        return err(NEED, 409)
    track("exported")
    return send_file(BytesIO(engine.report_xlsx(f)), as_attachment=True, download_name="finova_financial_report.xlsx", mimetype=XLSX)


@app.post("/api/export/plan")
@login_required
def export_plan():
    f = need_finance()
    if not f:
        return err(NEED, 409)
    d = request.get_json(silent=True) or {}
    try:
        data = engine.plan_xlsx(f, d.get("goals"), d.get("chosen"), d.get("assumptions"))
    except ValueError as e:
        return err(str(e), 422)
    track("exported")
    return send_file(BytesIO(data), as_attachment=True, download_name="finova_savings_investment_plan.xlsx", mimetype=XLSX)


# ------------------------------------------------------------ evaluation
def summary():
    rows = db().execute("SELECT * FROM ratings").fetchall()
    n = len(rows)
    mine = db().execute("SELECT * FROM ratings WHERE user_id=?", (session.get("uid"),)).fetchone()
    avg = lambda k: round(sum(r[k] for r in rows) / n, 2) if n else None
    return {"count": n, "overall": round(sum(r["avg"] for r in rows) / n, 2) if n else None,
            "criteria": {k: avg(k) for k in ("accuracy", "groundedness", "usability", "processing")},
            "flagged": sum(r["flagged"] for r in rows), "mine": dict(mine) if mine else None}


@app.route("/api/ratings", methods=["GET", "POST"])
@login_required
def ratings():
    if request.method == "POST":
        d = request.get_json(silent=True) or {}
        try:
            v = {k: int(d[k]) for k in ("accuracy", "groundedness", "usability", "processing")}
        except (KeyError, ValueError, TypeError):
            return err("Please rate all four criteria.")
        if any(not 1 <= x <= 5 for x in v.values()):
            return err("Ratings must be between 1 and 5 stars.")
        try:                       # one evaluation per account: the primary key makes this atomic even with two workers
            db().execute("INSERT INTO ratings(user_id,accuracy,groundedness,usability,processing,avg,comment,flagged,updated) VALUES(?,?,?,?,?,?,?,?,?)",
                         (session["uid"], *v.values(), sum(v.values()) / 4, str(d.get("comment", ""))[:1000], 1 if d.get("flagged") else 0, time.time()))
            db().commit()
        except sqlite3.IntegrityError:
            return err("You have already evaluated FINOVA. Each account can submit one evaluation.", 409)
    return jsonify(summary())


def pct_ms(name, q):
    xs = sorted(r["ms"] for r in db().execute("SELECT ms FROM metrics WHERE name=?", (name,)).fetchall())
    if not xs:
        return None
    return xs[min(len(xs) - 1, int(q * len(xs)))]


_acc_cache = {"t": 0, "v": None}


def accuracy():
    if time.time() - _acc_cache["t"] > 600 or not _acc_cache["v"]:
        t = time.perf_counter()
        good, total, fails = verify.run_checks(seed=7, n=25)
        _acc_cache.update(t=time.time(), v=(good, total, fails, (time.perf_counter() - t) * 1000))
    return _acc_cache["v"]


@app.get("/api/eval/dashboard")
@login_required
def eval_dashboard():
    good, total, fails, ver_ms = accuracy()
    # groundedness: (a) offline test of the rule-based narrative; (b) live LLM outputs logged in production
    sample = {"income": 25e6, "expenses": 12e6, "investments": 50e6, "assets": 120e6, "debt": 80e6, "debt_payment": 3e6, "years": 10, "liquidity": "medium", "risk": "medium", "debt_rate": 8}
    a = engine.analysis(sample)
    nar = narrative.analysis(a)
    ok, checked = engine.grounded_rate("\n".join([nar["table"], nar["chart"], nar["guidance"], nar["recommendations"]] + list(nar["scenarios"].values())), a)
    live = db().execute("SELECT SUM(g_ok) o, SUM(g_checked) c, SUM(rejected) r, COUNT(*) n FROM llm_log WHERE source IN ('gemini','partial') AND g_checked>0").fetchone()
    errs = db().execute("SELECT COUNT(*) c FROM llm_log WHERE error IS NOT NULL AND error!='not_configured'").fetchone()["c"]
    s = summary()
    users = db().execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    done = lambda e: db().execute("SELECT COUNT(DISTINCT user_id) c FROM events WHERE name=?", (e,)).fetchone()["c"]
    core = db().execute("SELECT COUNT(*) c FROM (SELECT user_id FROM events WHERE name IN ('finance_saved','results_viewed','goals_analyzed') GROUP BY user_id HAVING COUNT(DISTINCT name)=3)").fetchone()["c"]
    eng_avg = db().execute("SELECT AVG(ms) m, COUNT(*) c FROM metrics WHERE name='analysis_engine'").fetchone()
    ai_avg = db().execute("SELECT AVG(ms) m, COUNT(*) c FROM metrics WHERE name='ai_generation'").fetchone()
    slow = db().execute("SELECT COUNT(*) c FROM metrics WHERE (name IN ('analysis_engine','goals_engine','whatif_engine') AND ms>1000) OR (name='ai_generation' AND ms>20000)").fetchone()["c"]
    t = time.perf_counter()
    narrative.analysis(a)
    nar_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    engine.analysis(sample)
    eng_now = (time.perf_counter() - t) * 1000
    f1 = lambda x: f"{x:.0f} ms" if x is not None else "n/a"
    rows = [
        {"criterion": "Accuracy", "kpi": "Engine vs independent exact-arithmetic and closed-form recomputation (metrics, 5 scenarios, loans, goal plans, allocation)",
         "target": "≥ 98%", "actual": f"{good / total * 100:.2f}% ({good}/{total} checks)" + (f"; failed: {fails[0]}" if fails else ""), "pass": good / total >= 0.98},
        {"criterion": "Groundedness", "kpi": "Offline: money and % figures in the rule-based narrative that exist in Python outputs", "target": "≥ 95%",
         "actual": f"{ok / checked * 100:.1f}% ({ok}/{checked} figures)" if checked else "n/a", "pass": bool(checked) and ok / checked >= 0.95},
        {"criterion": "Groundedness", "kpi": "Live: figures in raw Gemini outputs matched to Python results (checked before any text is shown; ungrounded fields are discarded)", "target": "≥ 95%",
         "actual": (f"{live['o'] / live['c'] * 100:.1f}% ({live['o']}/{live['c']} figures, {live['n']} outputs, {live['r'] or 0} fields rejected)" if live["c"] else
                    ("No live Gemini output yet" if ai.configured() else "AI key not configured")),
         "pass": (live["o"] / live["c"] >= 0.95) if live["c"] else None},
        {"criterion": "Usability", "kpi": "Average user usability rating (1-5 stars)", "target": "≥ 4.0 / 5",
         "actual": f"{s['criteria']['usability']:.2f} / 5 ({s['count']} ratings)" if s["count"] else "No ratings yet", "pass": (s["criteria"]["usability"] >= 4.0) if s["count"] else None},
        {"criterion": "Usability", "kpi": "Task completion: users who saved finances, viewed results and analysed goals", "target": "≥ 80% of users",
         "actual": f"{core}/{users} users ({core / users * 100:.0f}%); saved {done('finance_saved')}, results {done('results_viewed')}, goals {done('goals_analyzed')}, export {done('exported')}" if users else "No users yet",
         "pass": (core / users >= 0.8) if users else None},
        {"criterion": "Processing Time", "kpi": "Calculation engine (5 scenarios, monthly simulation) - average / p95", "target": "≤ 1,000 ms",
         "actual": f"{f1(eng_avg['m'])} avg, {f1(pct_ms('analysis_engine', .95))} p95 over {eng_avg['c']} runs; now {eng_now:.0f} ms", "pass": (eng_avg["m"] or eng_now) <= 1000 and (pct_ms("analysis_engine", .95) or 0) <= 1000},
        {"criterion": "Processing Time", "kpi": "Rule-based narrative generation", "target": "≤ 500 ms", "actual": f"{nar_ms:.1f} ms", "pass": nar_ms <= 500},
        {"criterion": "Processing Time", "kpi": "AI generation latency (Gemini) - average / p95", "target": "≤ 20,000 ms",
         "actual": (f"{f1(ai_avg['m'])} avg, {f1(pct_ms('ai_generation', .95))} p95 over {ai_avg['c']} calls" if ai_avg["c"] else ("No AI calls yet" if ai.configured() else "AI key not configured")),
         "pass": (ai_avg["m"] <= 20000 and pct_ms("ai_generation", .95) <= 20000) if ai_avg["c"] else None},
        {"criterion": "Processing Time", "kpi": "Slow edge cases (engine > 1,000 ms or AI > 20,000 ms)", "target": "0", "actual": str(slow), "pass": slow == 0},
    ]
    return jsonify({"rows": rows, "summary": s, "ai_enabled": ai.configured(), "ai_errors": errs, "verify_ms": ver_ms})


# ---------------------------------------------------------------- support
IMG_SIG = ((b"\x89PNG\r\n\x1a\n", ".png"), (b"\xff\xd8\xff", ".jpg"), (b"GIF8", ".gif"), (b"RIFF", ".webp"))


@app.post("/api/support")
@login_required
def support():
    f, form = request.files.get("attachment"), request.form
    typ = form.get("type", "")
    if typ not in {t["label"] for t in FAQ["support_types"]}:
        return err("Please choose an issue type.")
    subject, desc, email = form.get("subject", "").strip(), form.get("description", "").strip(), form.get("email", "").strip()
    if len(subject) < 3 or len(desc) < 10:
        return err("Please add a subject and a more detailed description.")
    if not EMAIL_RE.match(email):
        return err("Please enter a valid email so we can reply.")
    if throttle(f"tk:{session['uid']}", 10, 3600, record=True):
        return too_many()
    fname = None
    if f and f.filename:
        head = f.read(16)
        f.seek(0)
        ext = next((e for sig, e in IMG_SIG if head.startswith(sig) and (sig != b"RIFF" or head[8:12] == b"WEBP")), None)
        if not ext:
            return err("Attachments must be real screenshots (png, jpg, gif or webp).")
        fname = f"{int(time.time())}_{secrets.token_hex(6)}{ext}"
        f.save(DATA_DIR / "uploads" / fname)
    now = time.time()
    cur = db().execute("INSERT INTO tickets(user_id,type,subject,description,email,attachment,status,created,updated) VALUES(?,?,?,?,?,?,'open',?,?)",
                       (session["uid"], typ, subject[:150], desc[:4000], email, fname, now, now))
    db().commit()
    tid = f"FIN-{cur.lastrowid:05d}"
    if os.getenv("SUPPORT_EMAIL"):
        send_mail(os.getenv("SUPPORT_EMAIL"), f"[{tid}] {typ}: {subject[:80]}", f"From: {email}\nType: {typ}\n\n{desc[:4000]}")
    return jsonify({"ok": True, "ticket": tid})


def ticket_json(r, admin=False):
    d = {"id": r["id"], "ref": f"FIN-{r['id']:05d}", "type": r["type"], "subject": r["subject"], "description": r["description"], "status": r["status"],
         "note": r["note"], "created": r["created"], "updated": r["updated"], "has_attachment": bool(r["attachment"])}
    if admin:
        d["email"] = r["email"]
    return d


@app.get("/api/support")
@login_required
def my_tickets():
    rows = db().execute("SELECT * FROM tickets WHERE user_id=? ORDER BY id DESC LIMIT 50", (session["uid"],)).fetchall()
    return jsonify({"tickets": [ticket_json(r) for r in rows]})


@app.get("/api/support/<int:tid>/attachment")
@login_required
def ticket_attachment(tid):
    r = db().execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
    if not r or not r["attachment"] or (r["user_id"] != session["uid"] and not is_admin(me())):
        return err("Not found.", 404)
    return send_from_directory(DATA_DIR / "uploads", r["attachment"])


@app.get("/api/admin/tickets")
@admin_required
def admin_tickets():
    rows = db().execute("SELECT * FROM tickets ORDER BY id DESC LIMIT 200").fetchall()
    return jsonify({"tickets": [ticket_json(r, True) for r in rows]})


@app.put("/api/admin/tickets/<int:tid>")
@admin_required
def admin_ticket_update(tid):
    d = request.get_json(silent=True) or {}
    if d.get("status") not in ("open", "in_progress", "resolved"):
        return err("Invalid status.")
    db().execute("UPDATE tickets SET status=?, note=?, updated=? WHERE id=?", (d["status"], str(d.get("note", ""))[:1000], time.time(), tid))
    db().commit()
    return jsonify({"ok": True})


# ------------------------------------------------------------------- chat
@app.post("/api/chat")
@login_required
def chat():
    d = request.get_json(silent=True) or {}
    msg = str(d.get("message", "")).strip()
    if not msg:
        return err("Please type a question.")
    if throttle(f"chat:{session['uid']}", 20, 60, record=True):
        return too_many()
    ctx, f = "", load_finance()
    if f and (f.get("income") or f.get("expenses")):                    # authorized data: the signed-in user's own only
        a = engine.analysis(f)
        slim = {"profile": a["profile"], "metrics": a["metrics"], "health": a["health"]["items"],
                "scenario_ranking": [{"scenario": s["title"], "net_cash_flow": s["net_cash_flow"], "final_net_worth": s["final_net_worth"],
                                      "assumptions": s["assumptions"]} for s in sorted(a["scenarios"], key=lambda s: s["rank"])],
                "reference_goals": a["goals"],
                "saved_plans": [json.loads(r["data"])["summary"] | {"name": r["name"]} for r in db().execute("SELECT name,data FROM plans WHERE user_id=? ORDER BY id DESC LIMIT 5", (session["uid"],))]}
        ctx = json.dumps(slim, default=str)
    t = time.perf_counter()
    res = ai.chat(msg, d.get("history"), KB, ctx)
    log_llm("chat", {"source": res["source"] if res["source"] == "gemini" else "rules", "error": res.get("error"), "ms": (time.perf_counter() - t) * 1000,
                     "grounded": res.get("grounded")})
    if res["source"] == "gemini":
        metric("ai_generation", (time.perf_counter() - t) * 1000)
    return jsonify(res)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG") == "1")
