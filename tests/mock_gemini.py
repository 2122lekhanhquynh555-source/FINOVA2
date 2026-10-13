"""Local fake of the Gemini generateContent endpoint, with switchable failure modes."""
import json, re, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer

STATE = {"mode": "ok", "calls": 0, "last_body": None, "last_headers": None, "fail_n": 0}


def _fmt(x):
    return f"{x:,.0f}"


def make_answer(body):
    prompt = body["contents"][-1]["parts"][0]["text"]
    sys_txt = (body.get("systemInstruction") or {}).get("parts", [{}])[0].get("text", "")
    if "extract a personal financial profile" in sys_txt:
        t = prompt.lower()
        out = {"fields": {}, "unclear": [], "questions": []}
        m = re.search(r"earn (\d+) million", t)
        if m: out["fields"]["income"] = int(m.group(1)) * 1_000_000
        m = re.search(r"spend (\d+) million", t)
        if m: out["fields"]["expenses"] = int(m.group(1)) * 1_000_000
        if "hallucinate" in t: out["fields"]["assets"] = 999_000_000   # not in the text -> must be rejected
        return json.dumps(out)
    if "review rows read from a user's spreadsheet" in sys_txt:
        return json.dumps({"mapping": {"Lương tháng": "income", "Weird": "debt"}, "remarks": ["Expenses look high."]})
    if "CALCULATION OUTPUT" in prompt:
        data = json.loads(prompt.split("CALCULATION OUTPUT (authoritative):\n", 1)[1])
        halluc = STATE["mode"] == "hallucinate"
        if "priority_order" in prompt:                                   # Task 2
            names = [r["name"] for r in data["ranking"]]
            pname = data["goals"][data["primary"]]["name"]
            if STATE["mode"] == "wrong_order": names = names[::-1]
            num = "7,777,777 VND" if halluc else _fmt(data["metrics"]["net_cash_flow"]) + " VND"
            return json.dumps({"priority_order": names, "ranking": f"Ranking uses cash flow {num}.", "primary": f"{pname} is the best fit. Cash flow {num}.", "process": "1. Save monthly."})
        if "explanation of the what-if" in prompt:                    # Task 3
            net = data["rows"][4]["adjusted"]
            return json.dumps({"text": f"Adjusted net cash flow is {'9,123,457' if halluc else _fmt(net)} VND."})
        if "secondary" in prompt.lower():
            return json.dumps({"text": "Secondary goal explanation."})
        return json.dumps({"table": f"Income is {_fmt(data['metrics']['income'])} VND.", "chart": "Chart text.",
                           "scenarios": {k: f"{k} scenario." for k in ("severe", "conservative", "baseline", "optimistic", "high")},
                           "guidance": "Guidance.", "recommendations": "Recommendations."})
    # chat
    return "MOCK-CHAT-REPLY | docs:" + ("DTI" if "DTI" in prompt else "none")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n))
        STATE["calls"] += 1; STATE["last_body"] = body; STATE["last_headers"] = dict(self.headers)
        mode = STATE["mode"]
        def send(code, obj):
            raw = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
        if mode == "always_500": return send(500, {"error": "boom"})
        if mode == "rate_limit_once" and STATE["calls"] == 1: return send(429, {"error": "quota"})
        if mode == "rate_limit_always": return send(429, {"error": "quota"})
        if mode == "bad_key": return send(403, {"error": {"message": "API key not valid"}})
        if mode == "timeout": time.sleep(2.5); return send(200, {})
        if mode == "blocked": return send(200, {"promptFeedback": {"blockReason": "SAFETY"}})
        if mode == "empty": return send(200, {"candidates": []})
        if mode == "not_json_body": raw = b"<html>oops</html>"; self.send_response(200); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        text = "this is not json {" if mode == "bad_json" else make_answer(body)
        send(200, {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]})


def start():
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"
