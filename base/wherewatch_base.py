#!/usr/bin/env python3
"""WhereWatch base station v0: photos in, "where is my X" answers out.

Standard library plus Pillow (for face blurring), nothing else to install.

  photos dropped into INBOX
    -> a local vision model (OpenAI-compatible llama-server with an mmproj)
       lists the THINGS in each photo and where they are
    -> faces are blurred before the photo is stored; the unblurred original
       is never kept (if faces cannot be located, the whole photo is blurred)
    -> SQLite index of things only (people are kept out by the prompt AND a
       word filter afterwards; a word filter cannot catch proper names or
       other languages, so this lowers the risk rather than guaranteeing it)
    -> the existing web app's /api/* (web/API.md) answers from real data,
       including /api/recap: the day in a few sentences (model-told story,
       index-computed "last seen" line).

Run:  python3 base/wherewatch_base.py --vision http://127.0.0.1:8095
Then open http://127.0.0.1:8090/ (web app) and drop photos into base/data/inbox/.
"""
import argparse
import base64
import datetime as dt
import html
import json
import math
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

from PIL import Image, ImageFilter, ImageOps

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

FACE_PROMPT = """Locate every human face or head in this photo, including small,
partial, turned-away or background ones, and faces on screens or posters.
Answer with JSON only:
{"people": <true if any person is visible at all, else false>,
 "faces": [[x1, y1, x2, y2], ...]}
Coordinates are integers from 0 to 1000, relative to the image width (x) and
height (y), top-left origin. Use {"people": false, "faces": []} if there are none."""


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


def ask_vision(url, model, path, timeout, prompt=PROMPT):
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    body = {
        "model": model,
        "temperature": 0,
        "max_tokens": 600,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
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


def face_boxes(answer, w, h):
    """Model boxes (0-1000) -> padded pixel boxes. None means "cannot trust
    this answer": the caller must then blur everything (fail closed).

    Only an answer of exactly the asked shape counts: a dict with a boolean
    "people" and a list "faces". Anything else, including a missing "people",
    is treated as unknown rather than as "no faces"."""
    if (not isinstance(answer, dict) or not isinstance(answer.get("people"), bool)
            or not isinstance(answer.get("faces"), list)):
        return None
    boxes = []
    for b in answer["faces"]:
        # One bad box spoils the whole answer: skipping it while keeping the
        # others would leave that face unblurred.
        if not isinstance(b, (list, tuple)) or len(b) != 4:
            return None
        try:
            x1, y1, x2, y2 = (float(v) for v in b)
        except (TypeError, ValueError):
            return None
        if not all(math.isfinite(v) and 0 <= v <= 1000 for v in (x1, y1, x2, y2)):
            return None
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        if x2 - x1 < 1 or y2 - y1 < 1:
            return None
        pw, ph = (x2 - x1) * 0.35, (y2 - y1) * 0.35  # pad: model boxes run tight
        boxes.append((max(0, int((x1 - pw) * w / 1000)), max(0, int((y1 - ph) * h / 1000)),
                      min(w, int((x2 + pw) * w / 1000)), min(h, int((y2 + ph) * h / 1000))))
    if answer["people"] and not boxes:
        return None  # people reported but not located
    return boxes


def blur_faces(path, answer):
    """Blur faces in place and drop all metadata. Returns how many regions were
    blurred, or -1 when the whole photo was blurred (fail closed)."""
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
    w, h = im.size
    boxes = face_boxes(answer, w, h)
    if boxes is None:
        im = im.filter(ImageFilter.GaussianBlur(max(w, h) / 40))
        n = -1
    else:
        for (x1, y1, x2, y2) in boxes:
            region = im.crop((x1, y1, x2, y2))
            # pixelate then blur: unrecoverable, still reads as "a face was here"
            small = region.resize((max(1, (x2 - x1) // 12), max(1, (y2 - y1) // 12)))
            region = small.resize(region.size).filter(ImageFilter.GaussianBlur(max(x2 - x1, y2 - y1) / 10))
            im.paste(region, (x1, y1))
        n = len(boxes)
    fmt = "PNG" if path.lower().endswith(".png") else "JPEG"
    im.save(path, fmt, **({"quality": 90} if fmt == "JPEG" else {}))  # no EXIF written
    return n


def normalize(src, dst):
    """Upright pixels, no metadata: what both model calls and the blur see, so
    face boxes land where the faces are even for rotated phone photos."""
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
    fmt = "PNG" if dst.lower().endswith(".png") else "JPEG"
    im.save(dst, fmt, **({"quality": 95} if fmt == "JPEG" else {}))


def index_photo(store, args, src):
    """The original never enters the served photos/ folder. It stays in the
    private inbox until a blurred copy has been published and indexed, so a
    crash at any point leaves nothing unblurred to serve, and the photo is
    simply retried on restart."""
    name = os.path.basename(src)
    if store.q("SELECT 1 FROM photos WHERE file=?", (name,)):
        os.remove(src)
        return
    when = taken_at(src)
    work = os.path.join(args.data, "staging", name)  # private, never served
    try:
        normalize(src, work)
    except Exception as e:  # unreadable image: do not keep it
        os.remove(src)
        print(f"[index] {name}: unreadable, deleted ({type(e).__name__})", flush=True)
        return
    try:
        result = ask_vision(args.vision, args.model, work, args.timeout)
        err = None
    except Exception as e:  # keep the photo, record why it was not indexed
        result, err = {"place": "", "objects": []}, f"{type(e).__name__}: {e}"[:300]
    # Faces are blurred before the photo is published; if the face check
    # itself fails, the whole photo is blurred rather than kept as is.
    try:
        faces = ask_vision(args.vision, args.model, work, args.timeout, FACE_PROMPT)
    except Exception as e:
        faces = None
        err = (err + "; " if err else "") + f"face check failed, whole photo blurred: {type(e).__name__}"[:200]
    blurred = blur_faces(work, faces)
    os.replace(work, os.path.join(args.data, "photos", name))  # atomic publish, same filesystem
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
    os.remove(src)  # only now: the blurred copy is published and indexed
    faces_note = (", whole photo blurred" if blurred < 0 else
                  f", {blurred} face(s) blurred" if blurred else "")
    print(f"[index] {name} @ {when}: {kept} things at '{place}'" + faces_note
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
        # File first: if it cannot be deleted, keep its rows so the next pass
        # tries again, instead of leaving an untracked photo on disk forever.
        try:
            os.remove(os.path.join(args.data, "photos", f))
        except FileNotFoundError:
            pass
        except OSError as e:
            print(f"[retention] could not delete {f}, will retry: {e}", flush=True)
            continue
        store.q("DELETE FROM sightings WHERE photo_id=?", (pid,))
        store.q("DELETE FROM photos WHERE id=?", (pid,))


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


RECAP_PROMPT = """You write a short recap of someone's day for a "where did I
leave my things" memory. Below is everything their camera noticed that day:
time, thing, and where it lay. Write 1 to 3 plain sentences addressed to them,
in time order. Only a thing listed at two or more different places moved: say
where it went and when. A thing listed at one place did not move: just say
where it was ("your wallet was on the desk at 09:40"). Use only things, places
and times from the list and never add anything that is not in it. NEVER
mention or guess at people: no names, and do not use the words he, she, they,
them or their. Do NOT end with a summary of where things are now; that line is
added separately. Plain text only: no lists, no markdown.

Sightings:
"""

# The model may only rephrase the day: every word of its answer must be a time,
# a word from that day's thing names, places and positions, or one of these.
# A name, a family word, another language or invented detail fails the check
# and the plain summary is shown instead. An allowlist, because a list of
# person words can never be complete.
RECAP_WORDS = frozenset("""
your you yours a an the and or but then later again also still back so
was were is are has have had been be being moved move moves went go goes came
come stayed stays remained remain left lay lain sat sitting lying spent found
appeared showed turned ended
to from at on in into onto by near beside next under over behind between
across of off up down with without inside outside top bottom side front
it its it's this that these those same another other there here where when
while after before until since around about first then finally last earlier
day today morning noon midday afternoon evening night am pm o'clock all both
each one two three several some no not only just again once twice
place spot seen noticed spotted""".split())

RECAP_LINES = 120          # newest changes the model sees; older ones are summarised by count
RECAP_FAIL_SECONDS = 300   # after a model failure, that day gets the plain recap this long
_recap_cache = {}          # key -> finished recap (model or deterministic fallback)
_recap_backoff = {}        # day -> time until which the model is not asked again
_recap_inflight = {}       # key -> Event, so concurrent requests share one model call
_recap_lock = threading.Lock()


def ask_text(url, model, prompt, timeout):
    """Text-only chat completion on the same local server the photos use."""
    body = {"model": model, "temperature": 0, "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions",
                                 json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["choices"][0]["message"]["content"] or ""


def day_sightings(store, day):
    """(id, name, place, relative_position, seen_at) for one day, oldest first."""
    return store.q("""SELECT s.id, s.name, s.place, s.relative_position, s.seen_at
                      FROM sightings s JOIN photos p ON p.id = s.photo_id
                      WHERE substr(s.seen_at, 1, 10) = ?
                      ORDER BY s.seen_at, s.id""", (day,))


def hhmm(iso):
    return iso[11:16]


def digest(rows):
    """The model's input: a line each time a thing is seen somewhere new (one
    photo often holds several things, so this is tracked per thing), stored
    HTML escapes turned back into text."""
    lines, where_now = [], {}
    for name, place, rel, seen in rows:
        if where_now.get(name) == place:
            continue
        where_now[name] = place
        where = html.unescape(place or "an unknown spot") + (f" ({html.unescape(rel)})" if rel else "")
        lines.append(f"{hhmm(seen)} {html.unescape(name)} at {where}")
    if len(lines) > RECAP_LINES:
        lines = [f"(plus {len(lines) - RECAP_LINES} earlier changes)"] + lines[-RECAP_LINES:]
    return "\n".join(lines)


def last_seen(rows, limit=6):
    """The one line that must be right, so it never comes from the model: the
    newest place of the most recently seen things, straight from the index.
    Built from stored values, which were escaped when they were indexed."""
    last = {}
    for name, place, _rel, seen in rows:
        last[name] = (place, seen)
    recent = sorted(last.items(), key=lambda kv: kv[1][1], reverse=True)
    more = len(recent) - limit
    listed = "; ".join(f"{n} at {p or 'an unknown spot'} ({hhmm(s)})" for n, (p, s) in recent[:limit])
    return f"Last seen: {listed}" + (f"; and {more} more." if more > 0 else ".")


def plain_recap(rows):
    """No model needed: counts plus the last-seen line."""
    if not rows:
        return "Nothing seen that day."
    things = len({r[0] for r in rows})
    places = len({r[1] for r in rows if r[1]})
    return (f"{things} thing{'s' if things != 1 else ''} seen in {places} "
            f"place{'s' if places != 1 else ''} between {hhmm(rows[0][3])} and "
            f"{hhmm(rows[-1][3])}. " + last_seen(rows))


def tokens(text):
    return re.findall(r"[^\W\d_]+(?:'[^\W\d_]+)?|\d+", text.lower())


def model_text_ok(text, rows):
    """True only if every word is a time, a word from the day's sightings or a
    RECAP_WORDS word. Plural and possessive forms of known words count."""
    known = set(RECAP_WORDS)
    for name, place, rel, _seen in rows:
        known.update(tokens(html.unescape(f"{name} {place or ''} {rel or ''}")))
    for w in tokens(text):
        if w.isdigit() or w in known:
            continue
        base = w[:-2] if w.endswith("'s") else w
        if base in known or base.rstrip("s") in known or base + "s" in known or base + "es" in known:
            continue
        return False
    return True


_TIME = re.compile(r"\b(\d{1,2})[:.](\d{2})\b")
_CLAUSE = re.compile(r"[.!?;,]|\b(?:and|then|while|but)\b", re.I)


def _words(text):
    """tokens() with possessives folded: "sofa's" -> "sofa"."""
    return [w[:-2] if w.endswith("'s") else w for w in tokens(text)]


def _forms(phrase):
    """A name's words, plus singular/plural forms of its last word."""
    *head, last = phrase
    alts = {last, last + "s", last + "es"}
    if last.endswith("es"):
        alts.add(last[:-2])
    if last.endswith("s"):
        alts.add(last[:-1])
    return {tuple(head) + (a,) for a in alts if a}


def _take(words, phrases):
    """Find whole phrases (longest first) in a word list; return what was found
    and the words left over, with every found phrase removed."""
    found, left, i = set(), list(words), 0
    by_len = sorted(phrases.items(), key=lambda kv: -len(kv[0]))
    while i < len(left):
        for form, canon in by_len:
            n = len(form)
            if tuple(left[i:i + n]) == form:
                found.add(canon)
                left[i:i + n] = [None] * n
                break
        i += 1
    return found, [w for w in left if w is not None]


def claims_ok(text, rows):
    """The model's sentences must be TRUE of the day, not only built from its
    words (Codex review of #17: "your keys moved from the kitchen counter to the
    desk at 23:59" passes the word check when keys and a wallet were each seen
    once). Clause by clause: every thing it names was seen at every place it
    names, and every time it gives is a time one of those things was seen (at a
    named place, when it names one). A clause without a thing takes the previous
    clause's ("...and later moved to the desk"). A clause that names a place or
    a time with no thing to tie it to, or a fragment of a place's name ("the
    hallway" for "hallway table"), cannot be checked and fails."""
    seen = {}                                   # thing -> place -> {HH:MM}
    for name, place, _rel, ts in rows:          # stored values are HTML-escaped
        thing = " ".join(_words(html.unescape(name)))
        where = " ".join(_words(html.unescape(place or "")))
        seen.setdefault(thing, {}).setdefault(where, set()).add(hhmm(ts))
    thing_forms = {f: t for t in seen for f in _forms(tuple(t.split()))}
    place_forms = {tuple(p.split()): p for t in seen for p in seen[t] if p}
    place_only = ({w for p in place_forms.values() for w in p.split()}
                  - {w for t in seen for w in t.split()}
                  - {w for _n, _p, rel, _t in rows for w in _words(html.unescape(rel or ""))}
                  - RECAP_WORDS)
    things = set()
    for clause in _CLAUSE.split(text):
        times = {f"{int(h):02d}:{m}" for h, m in _TIME.findall(clause)}
        words = [w for w in _words(_TIME.sub(" ", clause)) if not w.isdigit()]
        named, left = _take(words, thing_forms)
        places, left = _take(left, place_forms)
        if any(w in place_only for w in left):
            return False                        # part of a place's name, not the place
        things = named or things
        if (places or times) and not things:
            return False                        # nothing to check the claim against
        for t in things:
            if any(p not in seen[t] for p in places):
                return False                    # that thing was never seen there
        for tm in times:
            if not any(tm in seen[t][p] for t in things for p in (places or seen[t])):
                return False                    # no sighting of it at that time
    return True


def model_story(text, rows):
    """The model's answer, or ValueError if it cannot be shown: reasoning left
    in (a thinking template that opens <think> in the prompt, or a cut-off),
    empty, mentioning a person, using words the day does not contain, or
    claiming a thing was somewhere, or at a time, it was not."""
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    if "<think" in text:
        raise ValueError("unfinished reasoning")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise ValueError("empty")
    if PEOPLE.search(text) or not model_text_ok(text, rows):
        raise ValueError("words outside the day's sightings")
    if not claims_ok(text, rows):
        raise ValueError("a claim the day's sightings do not support")
    return text


def recap(store, args, day):
    """The day in a few sentences: the local model retells what moved, and the
    last-seen line is always computed from the index, never written by the
    model. Things, not people: the model sees only that day's index rows, and
    its answer is shown only if every word comes from those rows or a small
    fixed vocabulary, so it cannot add a person the index does not already
    hold; anything else gets the plain summary."""
    full = day_sightings(store, day)
    rows = [r[1:] for r in full]
    counts = {"day": day, "sightings": len(rows), "things": len({r[0] for r in rows}),
              "places": len({r[1] for r in rows if r[1]})}
    plain = {**counts, "summary": plain_recap(rows), "source": "plain"}
    if not rows:
        return plain
    ids = [r[0] for r in full]
    key = (day, len(ids), sum(ids), max(ids))  # this day's rows only: any add or delete changes it
    wait_s = getattr(args, "recap_timeout", 60) + 5
    while True:
        with _recap_lock:
            if key in _recap_cache:
                return _recap_cache[key]
            if _recap_backoff.get(day, 0) > time.time():
                return plain
            ev = _recap_inflight.get(key)
            if ev is None:
                ev = _recap_inflight[key] = threading.Event()
                break
        if not ev.wait(wait_s):  # another request is still asking the model
            return plain
    try:
        try:
            text = ask_text(args.vision, args.model, RECAP_PROMPT + digest(rows),
                            getattr(args, "recap_timeout", 60))
        except Exception as e:  # model down or slow: plain for this day for a while
            print(f"[recap] {day}: model unavailable, plain summary ({type(e).__name__})", flush=True)
            with _recap_lock:
                _recap_backoff[day] = time.time() + RECAP_FAIL_SECONDS
            return plain
        try:
            # The model tells the story; where things are now comes from the index.
            out = {**counts, "summary": clean(model_story(text, rows), 600) + " " + last_seen(rows),
                   "source": "model"}
        except ValueError as e:  # same input, same answer at temperature 0: keep the plain one
            print(f"[recap] {day}: model answer not shown ({e}), plain summary", flush=True)
            out = plain
        with _recap_lock:
            if len(_recap_cache) > 64:
                _recap_cache.clear()
            _recap_cache[key] = out
            _recap_backoff.pop(day, None)
        return out
    finally:  # whatever happened, release anyone waiting on this key
        with _recap_lock:
            _recap_inflight.pop(key, None)
        ev.set()


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
            if u.path == "/api/recap":
                day = qs.get("day", [dt.date.today().isoformat()])[0]
                try:
                    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
                        raise ValueError
                    dt.date.fromisoformat(day)
                except ValueError:
                    return self.send_json({"error": "day must be YYYY-MM-DD"}, 400)
                return self.send_json(recap(store, args, day))
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
            # Serve only photos that finished the blur and are in the index.
            if not store.q("SELECT 1 FROM photos WHERE file=?", (name,)) or not os.path.isfile(p):
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
    ap.add_argument("--recap-timeout", type=float, default=60.0,
                    help="seconds the day recap waits for the model before using the plain summary")
    args = ap.parse_args()
    for d in ("inbox", "photos", "staging"):
        os.makedirs(os.path.join(args.data, d), exist_ok=True)
    # Staging copies left by a crash are unblurred work files: delete them.
    # Their originals are still in the inbox and get processed again.
    staging = os.path.join(args.data, "staging")
    for f in os.listdir(staging):
        os.remove(os.path.join(staging, f))
    store = Store(os.path.join(args.data, "index.sqlite"))
    threading.Thread(target=watcher, args=(store, args), daemon=True).start()
    print(f"WhereWatch base v0 on http://{args.host}:{args.port}/  inbox: {os.path.join(args.data, 'inbox')}", flush=True)
    ThreadingHTTPServer((args.host, args.port), make_handler(store, args)).serve_forever()


if __name__ == "__main__":
    main()
