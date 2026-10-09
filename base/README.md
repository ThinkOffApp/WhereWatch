# WhereWatch base station v0

The "where did I leave my keys" loop, working end to end before any pendant
hardware exists: photos in, real answers out of the existing web app.

```
photo -> base/data/inbox/  ->  local vision model lists the THINGS and where they lie
                           ->  SQLite index (no people, ever)
                           ->  web/ app's /api/* answers from it (web/API.md)
```

## Run

You need an OpenAI-compatible vision server. Tested with llama.cpp's
`llama-server` and Qwen3-VL-8B-Instruct (Q8_0 + its F16 mmproj):

```
llama-server -m Qwen3VL-8B-Instruct-Q8_0.gguf --mmproj mmproj-Qwen3VL-8B-Instruct-F16.gguf \
  -ngl 999 -c 16384 --host 127.0.0.1 --port 8095 --alias qwen3-vl -np 2
```

Then, with Python 3 and Pillow (the only dependency, used to blur faces):

```
python3 base/wherewatch_base.py --vision http://127.0.0.1:8095
```

Open http://127.0.0.1:8090/ and drop photos into `base/data/inbox/`. Each photo
is indexed in a few seconds (about 4.8 s each on one DGX Spark with the setup
above) and moves to `base/data/photos/`.

## What it does today

- `/api/ask`, `/api/objects`, `/api/timeline`, `/api/status` and
  `POST /api/retention` answer from real data. `/api/checks` ("Did I?") returns
  an empty list until actions (locked, switched off) are indexed.
- `/api/recap` is the Timeline's "Your day" card: the same local model, asked
  in plain text, tells the day's story in 1-3 sentences (what moved, when).
  The "Last seen: ..." line after it is computed from the index and never
  written by the model, because the one fact that must be right is where things
  are now (a live test caught Qwen3-VL-8B claiming everything ended up on the
  desk). The model sees only the day's people-free sightings, and its answer
  is shown only if every word in it is a time, a word from that day's thing
  names, places and positions, or one of a small fixed set of narrative words
  (`RECAP_WORDS`). So a name, a family word, another language, leftover
  `<think>` reasoning or an invented detail all get the plain summary instead;
  an allowlist, because a list of person words can never be complete. The
  plain summary is also used when the model is unreachable or slower than
  `--recap-timeout` seconds (default 60); then that day is not retried for 5
  minutes. A recap is cached until that day's own sightings change (another
  day's photos do not invalidate it), and simultaneous requests share one
  model call. Measured: about 4 s for a 7-sighting day on one DGX Spark.
- Photo time comes from the JPEG's EXIF date, else the file time.
- Retention deletes photos and their index rows after N days (default 30).
- Everything binds to 127.0.0.1. Nothing leaves the box.

## Things, not people

People are kept out of the index three ways: the prompt tells the model to skip
people and anything worn or held, any thing whose name or position mentions a
person is dropped, and a place described by a person is blanked. `test_base.py`
pins that filter. Limit: the filter works on English words, so a proper name
("Anna's bag") or another language can get past it. It lowers the risk; it is
not a guarantee. A closed list of allowed thing types would be the stronger
next step.

Photos themselves: faces are blurred before a photo is published (petrus's
call, 7 Oct 2026). Each photo is first turned upright and stripped of metadata
into a private `staging/` copy; both model calls read that copy, so face boxes
match the pixels even for rotated phone photos. Each face box is padded,
pixelated and blurred. If the model says people are present but gives no
usable boxes, the face check fails, its answer is not exactly the asked shape
(a boolean "people" and a list "faces"), or any box is malformed, not finite
or outside 0-1000, the whole photo is blurred (fail closed). Limit: when the
model answers well-formed "no people" but missed a face, nothing is blurred.
Face blurring is best effort, as good as the model's eyes, not a guarantee. Only then is the copy moved into the served `photos/` folder in one
atomic step and indexed; the original stays in the private inbox until that
point and is deleted afterwards, so a crash leaves nothing unblurred to serve
and the photo is simply retried. `/photos/` serves only files that are in the
index. Measured cost: 6 photos in 29 s with the face check (about 4.8 s each)
against 21 s without it.

## Test

```
python3 -m unittest base/test_base.py
```
