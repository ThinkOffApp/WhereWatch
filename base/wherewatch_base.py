#!/usr/bin/env python3
"""WhereWatch base station v0: photos in, "where is my X" answers out.

Standard library only, so it runs on any base station without installs.

  photos dropped into INBOX
    -> a local vision model (OpenAI-compatible llama-server with an mmproj)
       lists the THINGS in each photo and where they are
    -> SQLite index (people are never stored: dropped in the prompt AND by a
       name filter afterwards, so "where is Anna" stays unanswerable)
    -> the existing web app's /api/* (web/API.md) answers from real data.

Run:  python3 base/wherewatch_base.py --vision http://127.0.0.1:8095
Then open http://127.0.0.1:8090/ (web app) and drop photos into base/data/inbox/.
"""
import argparse
import base64
import datetime as dt
import html
import json
import mimetypes
import os
import re
import shutil
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(os.path.dirname(HERE), "web")
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}

# "Things, not people - by design." Any object whose name matches is dropped.
# Person nouns, pronouns and wear/hold verbs only: body-part words like "arm"
# or "head" would also drop real places ("the arm of the sofa").
PEOPLE = re.compile(
    r"\b(person|persons|people|man|men|woman|women|boy|boys|girl|girls|child|"
    r"children|kid|kids|baby|babies|face|faces|human|humans|someone|somebody|"
    r"selfie|he|she|him|her|his|hers|they|them|their|"
    r"wearing|worn|wears|holding|held|holds|carrying|carried)\b", re.I)

PROMPT = """You index photos for a "where did I leave my things" memory.
List the portable personal THINGS visible in this photo that someone could
later lose or look for (keys, wallet, phone, glasses, headphones, bag, charger,
remote, mug, book, passport, bottle, ...). Ignore furniture, walls and fixed
fittings except as places. NEVER mention, describe or count people, faces or
body parts; skip them entirely. Skip any thing that is being worn or held:
only list things that are lying somewhere, and describe where they lie
without referring to a person.

Answer with JSON only, no prose:
{"place": "<the room or spot, e.g. hallway table, kitchen counter>",
 "objects": [{"name": "<short common noun, lower case, e.g. keys>",
              "aliases": ["<other words someone might ask with>"],
              "relative_position": "<where exactly, e.g. beside the bowl>",
              "confidence": <0.0-1.0>}]}
If nothing qualifies, return {"place": "...", "objects": []}."""


def clean(s, limit=80):
    """Model text goes into the web app's innerHTML: strip markup, cap length."""
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return html.escape(s[:limit], quote=True)


class Store:
    def __init__(self, path):
        self.lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS photos(
              id INTEGER PRIMARY KEY, file TEXT UNIQUE, taken_at TEXT,
              place TEXT, indexed_at TEXT, error TEXT);
            CREATE TABLE IF NOT EXISTS sightings(
              id INTEGER PRIMARY KEY, photo_id INTEGER REFERENCES photos(id),
              name TEXT, aliases TEXT, place TEXT, relative_position TEXT,
              confidence REAL, seen_at TEXT);
            CREATE INDEX IF NOT EXISTS s_name ON sightings(name);
            CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
        """)

    def q(self, sql, args=()):
        with self.lock:
            cur = self.db.execute(sql, args)
            rows = cur.fetchall()
            self.db.commit()
            return rows

    def retention_days(self):
        r = self.q("SELECT v FROM settings WHERE k='retention_days'")
        return int(r[0][0]) if r else 30


def taken_at(path):
    """Photo time: EXIF DateTimeOriginal for JPEGs, else file mtime."""
    try:
        with open(path, "rb") as f:
            head = f.read(256 * 1024)
        m = re.search(rb"(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})", head)
        if m:
            y, mo, d, h, mi, s = (int(x) for x in m.groups())
            return dt.datetime(y, mo, d, h, mi, s).isoformat()
    except (OSError, ValueError):
        pass
    return dt.datetime.fromtimestamp(os.path.getmtime(path)).replace(microsecond=0).isoformat()


def ask_vision(url, model, path, timeout):
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    body = {
        "model": model,
        "temperature": 0,
        "max_tokens": 600,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
    }
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions",
                                 json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        text = json.load(r)["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in model answer: " + text[:200])
    return json.loads(m.group(0))


def index_photo(store, args, src):
    name = os.path.basename(src)
    if store.q("SELECT 1 FROM photos WHERE file=?", (name,)):
        os.remove(src)
        return
    when = taken_at(src)
    dst = os.path.join(args.data, "photos", name)
    shutil.move(src, dst)
    try:
        result = ask_vision(args.vision, args.model, dst, args.timeout)
        err = None
    except Exception as e:  # keep the photo, record why it was not indexed
        result, err = {"place": "", "objects": []}, f"{type(e).__name__}: {e}"[:300]
    place = clean(result.get("place"))
    if PEOPLE.search(place):  # a place described by a person is no place
        place = ""
    store.q("INSERT INTO photos(file,taken_at,place,indexed_at,error) VALUES(?,?,?,?,?)",
            (name, when, place, dt.datetime.now().replace(microsecond=0).isoformat(), err))
    pid = store.q("SELECT id FROM photos WHERE file=?", (name,))[0][0]
    kept = dropped = 0
    for o in result.get("objects") or []:
        if not isinstance(o, dict):
            continue
        obj = clean(o.get("name"), 40).lower()
        aliases = [clean(a, 40).lower() for a in (o.get("aliases") or []) if isinstance(a, str)]
        rel = clean(o.get("relative_position"))
        # Drop the whole sighting if any field refers to a person: a worn or
        # held thing is not "left" anywhere, and the index must never hold
        # people, not even inside a position description.
        if (not obj or PEOPLE.search(obj) or PEOPLE.search(rel)
                or any(PEOPLE.search(a) for a in aliases)):
            dropped += 1
            continue
        try:
            conf = max(0.0, min(1.0, float(o.get("confidence", 0.5))))
        except (TypeError, ValueError):
            conf = 0.5
        store.q("INSERT INTO sightings(photo_id,name,aliases,place,relative_position,confidence,seen_at)"
                " VALUES(?,?,?,?,?,?,?)",
                (pid, obj, json.dumps(aliases), place, rel, conf, when))
        kept += 1
    print(f"[index] {name} @ {when}: {kept} things at '{place}'"
          + (f", {dropped} dropped" if dropped else "") + (f", ERROR {err}" if err else ""), flush=True)


def watcher(store, args):
    inbox = os.path.join(args.data, "inbox")
    while True:
        for f in sorted(os.listdir(inbox)):
            p = os.path.join(inbox, f)
            if os.path.splitext(f)[1].lower() in IMAGE_EXT and os.path.isfile(p):
                # skip files still being copied in
                if time.time() - os.path.getmtime(p) < 2:
                    continue
                index_photo(store, args, p)
        prune(store, args)
        time.sleep(args.poll)


def prune(store, args):
    cutoff = (dt.datetime.now() - dt.timedelta(days=store.retention_days())).isoformat()
    for pid, f in store.q("SELECT id,file FROM photos WHERE taken_at < ?", (cutoff,)):
        store.q("DELETE FROM sightings WHERE photo_id=?", (pid,))
        store.q("DELETE FROM photos WHERE id=?", (pid,))
        try:
            os.remove(os.path.join(args.data, "photos", f))
        except OSError:
            pass


def nice_time(iso):
    t = dt.datetime.fromisoformat(iso)
    today = dt.date.today()
    if t.date() == today:
        return t.strftime("%H:%M")
    if (today - t.date()).days < 7:
        return t.strftime("%a %H:%M")
    return t.strftime("%d %b %H:%M")


def words(q):
    stop = {"where", "are", "is", "my", "the", "did", "i", "leave", "put", "a", "an", "last", "seen"}
    return [w for w in re.findall(r"[a-z]+", q.lower()) if w not in stop]


def match(name, aliases, terms):
    cands = [name] + json.loads(aliases or "[]")
    for t in terms:
        for c in cands:
            # "key" matches "keys", "car keys" matches "keys"
            if t == c or t.rstrip("s") == c.rstrip("s") or t in c.split() or c in t:
                return True
    return False


def make_handler(store, args):
    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=WEB, **k)

        def log_message(self, fmt, *a):
            pass

        def send_json(self, obj, code=200):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(u.query)
            if u.path.startswith("/photos/"):
                return self.photo(u.path[len("/photos/"):])
            if u.path == "/api/ask":
                return self.send_json(self.ask(qs.get("q", [""])[0]))
            if u.path == "/api/objects":
                return self.send_json(self.objects())
            if u.path == "/api/timeline":
                return self.send_json(self.timeline(qs.get("day", [None])[0]))
            if u.path == "/api/checks":
                return self.send_json({"checks": []})  # "Did I?" needs actions, not built yet
            if u.path == "/api/status":
                return self.send_json(self.status())
            if u.path.startswith("/api/"):
                return self.send_json({"error": "not found"}, 404)
            return super().do_GET()

        def do_POST(self):
            if self.path == "/api/retention":
                n = int(self.headers.get("Content-Length", 0))
                try:
                    days = int(json.loads(self.rfile.read(n) or b"{}")["days"])
                    if not 1 <= days <= 3650:
                        raise ValueError
                except (ValueError, KeyError, TypeError):
                    return self.send_json({"ok": False}, 400)
                store.q("INSERT OR REPLACE INTO settings(k,v) VALUES('retention_days',?)", (str(days),))
                prune(store, args)
                return self.send_json({"ok": True})
            return self.send_json({"error": "not found"}, 404)

        def photo(self, name):
            name = os.path.basename(urllib.parse.unquote(name))
            p = os.path.join(args.data, "photos", name)
            if not os.path.isfile(p):
                return self.send_json({"error": "no photo"}, 404)
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(p)[0] or "image/jpeg")
            self.send_header("Content-Length", str(os.path.getsize(p)))
            self.end_headers()
            with open(p, "rb") as f:
                shutil.copyfileobj(f, self.wfile)

        def rows(self):
            return store.q("""SELECT s.name, s.aliases, s.place, s.relative_position,
                                     s.confidence, s.seen_at, p.file
                              FROM sightings s JOIN photos p ON p.id = s.photo_id
                              ORDER BY s.seen_at DESC""")

        def ask(self, q):
            terms = words(q)
            for name, aliases, place, rel, conf, seen, f in self.rows():
                if terms and match(name, aliases, terms):
                    return {"query": q, "found": True, "object": name, "place": place,
                            "relative_position": rel, "photo_url": "/photos/" + f,
                            "observed_at": nice_time(seen), "confidence": conf}
            return {"query": q, "found": False}

        def objects(self):
            latest = {}
            for name, _a, place, _r, _c, seen, f in self.rows():
                latest.setdefault(name, {"name": name, "last_place": place, "last_seen": nice_time(seen),
                                         "photo_url": "/photos/" + f, "pin": {"kind": "place", "place": place}})
            return {"objects": list(latest.values())}

        def timeline(self, day):
            day = day or dt.date.today().isoformat()
            ev = [{"time": nice_time(seen), "object": name, "action": "seen", "place": place,
                   "relative_position": rel, "photo_url": "/photos/" + f, "confidence": conf}
                  for name, _a, place, rel, conf, seen, f in self.rows() if seen.startswith(day)]
            return {"day": day, "events": ev}

        def status(self):
            last = store.q("SELECT MAX(indexed_at) FROM photos")[0][0]
            used = sum(os.path.getsize(os.path.join(args.data, "photos", f))
                       for f in os.listdir(os.path.join(args.data, "photos")))
            return {"pendant_online": False, "battery_pct": None, "mode": "stills",
                    "last_frame_at": nice_time(last) if last else "never",
                    "disk_used_gb": round(used / 1e9, 2), "retention_days": store.retention_days()}
    return H


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vision", required=True, help="OpenAI-compatible vision server, e.g. http://127.0.0.1:8095")
    ap.add_argument("--model", default="qwen3-vl", help="model name sent to the server")
    ap.add_argument("--data", default=os.path.join(HERE, "data"))
    ap.add_argument("--host", default="127.0.0.1", help="bind address (keep local; nothing leaves the box)")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--poll", type=float, default=3.0)
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()
    for d in ("inbox", "photos"):
        os.makedirs(os.path.join(args.data, d), exist_ok=True)
    store = Store(os.path.join(args.data, "index.sqlite"))
    threading.Thread(target=watcher, args=(store, args), daemon=True).start()
    print(f"WhereWatch base v0 on http://{args.host}:{args.port}/  inbox: {os.path.join(args.data, 'inbox')}", flush=True)
    ThreadingHTTPServer((args.host, args.port), make_handler(store, args)).serve_forever()


if __name__ == "__main__":
    main()
