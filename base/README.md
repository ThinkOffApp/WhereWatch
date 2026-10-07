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
is indexed in a few seconds (about 3.5 s each on one DGX Spark with the setup
above) and moves to `base/data/photos/`.

## What it does today

- `/api/ask`, `/api/objects`, `/api/timeline`, `/api/status` and
  `POST /api/retention` answer from real data. `/api/checks` ("Did I?") returns
  an empty list until actions (locked, switched off) are indexed.
- Photo time comes from the JPEG's EXIF date, else the file time.
- Retention deletes photos and their index rows after N days (default 30).
- Everything binds to 127.0.0.1. Nothing leaves the box.

## Things, not people

People are kept out of the index three ways: the prompt tells the model to skip
people and anything worn or held, any thing whose name or position mentions a
person is dropped, and a place described by a person is blanked. `test_base.py`
pins that filter.

Photos themselves: faces are blurred before a photo is stored (petrus's call,
7 Oct 2026). The model is asked for every face or head box; each box is padded,
pixelated and blurred, and the unblurred original is never kept. If the model
says people are present but gives no usable boxes, or the face check fails,
the whole photo is blurred instead (fail closed). Metadata is dropped on save.
This roughly doubles indexing time (two model calls per photo).

## Test

```
python3 -m unittest base/test_base.py
```
