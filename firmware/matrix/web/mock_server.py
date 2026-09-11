#!/usr/bin/env python3
"""Mock of the board's API for testing index.html in a browser without the XIAO.
Serves index.html at / and fakes the endpoints of API.md with an animated rainbow frame.
Usage: python3 mock_server.py [port]  (default 8090)"""
import json, math, os, sys, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = {"mode": 0, "modeName": "rainbow", "brightness": 40, "serpentine": 0, "color": "FF2D95", "mic": 1, "cam": 1}
NAMES = ["rainbow", "heart", "camera"]

def hsv(h):
    i = int(h * 6) % 6; f = h * 6 - int(h * 6)
    p, q, t = 0, 1 - f, f
    r, g, b = [(1, t, p), (q, 1, p), (p, 1, t), (p, q, 1), (t, p, 1), (1, p, q)][i]
    return "%02X%02X%02X" % (int(r * 255), int(g * 255), int(b * 255))

def pixels():
    t = time.time()
    if STATE["mode"] == 0:
        return [hsv(((x + y) / 16 + t / 4) % 1) for y in range(8) for x in range(8)]
    if STATE["mode"] == 1:
        heart = json.load(open(os.path.join(HERE, "..", "heart", "heart-v2.json")))["rows"]
        pulse = 0.6 + 0.4 * (0.5 + 0.5 * math.sin(t * 4))
        out = []
        for row in heart:
            for c in row:
                r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
                out.append("%02X%02X%02X" % (int(r * pulse), int(g * pulse), int(b * pulse)))
        return out
    return ["%02X%02X%02X" % ((v := int(127 + 127 * math.sin(t + x * 0.7 + y * 0.5))), v, v) for y in range(8) for x in range(8)]

class H(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/":
            body = open(os.path.join(HERE, "index.html"), "rb").read()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        if p == "/api/state": return self._json(STATE)
        if p == "/api/pixels": return self._json(pixels())
        self._json({"error": "not found"}, 404)
    def do_POST(self):
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/api/mode": STATE["mode"] = int(q["m"]); STATE["modeName"] = NAMES[STATE["mode"]]
            elif u.path == "/api/brightness": STATE["brightness"] = max(1, min(255, int(q["v"])))
            elif u.path == "/api/serpentine": STATE["serpentine"] = int(q["v"])
            elif u.path == "/api/color": STATE["color"] = q["hex"].upper()
            else: return self._json({"error": "not found"}, 404)
        except (KeyError, ValueError, IndexError) as e:
            return self._json({"error": str(e)}, 400)
        self._json(STATE)
    def log_message(self, *a): pass

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    print("mock matrix API on http://127.0.0.1:%d" % port, flush=True)
    HTTPServer(("127.0.0.1", port), H).serve_forever()
