# WhereWatch architecture

## Product constraint: only two devices

The finished WhereWatch system is deliberately just:

1. **Pendant** — ESP32-S3 + camera + battery, worn by the user.
2. **Raspberry Pi** — always-on local base station at home.

There is no required cloud service, GPU server, M5 cluster, desktop Mac, NAS,
or third appliance.

### Power and charging

Day-to-day physical setup is intentionally simple:

- **Raspberry Pi:** leave it plugged into power.
- **Pendant:** charge it over USB-C, then wear it untethered.

That is the entire power story. The Pi may have an SSD attached inside/under
its case, but this does not create another user-facing device.

On first setup the Pi joins Wi-Fi and is then intended to run headless. After
that, normal use should not require a monitor, keyboard, or Ethernet cable.

## Data path

```text
Pendant (ESP32-S3)
  camera + optional IMU
        |
        | low-rate JPEG/MJPEG + selected full-resolution stills
        v
Raspberry Pi
  Frigate / video ingest
        |
        | motion/events/keyframes
        v
  local vision model
        |
        | structured observations
        v
  object-memory database
        |
        v
"Where are my keys?"
        |
        v
last-seen location + image + timestamp
```

## What runs where

### Pendant

The pendant should stay simple because battery life matters more than local
AI performance.

It is responsible for:

- capturing images;
- JPEG compression;
- optional low-cost motion gating using frame differencing and/or an IMU;
- buffering briefly when Wi-Fi is unavailable;
- sending frames to the Pi;
- sleeping aggressively when nothing useful is happening.

It is **not** responsible for object recognition, semantic search, or running
a vision-language model.

### Raspberry Pi

The Pi is the complete local backend. It receives the pendant feed and does
the expensive work:

- Frigate/video ingest and timeline management;
- motion/event filtering and keyframe selection;
- local vision inference on useful stills;
- object and location extraction;
- last-seen/object-state tracking;
- local search and question answering;
- retention/deletion controls;
- the web/API/room-agent interface.

The design goal is that a Pi-class local model is sufficient for the core
question: **what object was seen, where was it, and when was it last seen?**
The exact model and quantization are implementation choices and should be
selected by measured Pi performance, not by making a larger machine part of
the product architecture.

## Frigate's role

Frigate is the cheap visual plumbing, not the memory itself.

Frigate can:

- ingest the pendant stream;
- decode frames;
- detect motion/events;
- keep short clips/snapshots;
- provide a timeline and event API.

WhereWatch adds the part Frigate does not provide by itself: a durable
*object-state memory*.

Example:

```text
OBJECT: black glasses case

11:31  in hand
11:32  placed on kitchen table
11:35  still on kitchen table
12:06  not observed

CURRENT LOCATION:
kitchen table, beside coffee machine
last positive observation: 11:35
```

This lets most queries return immediately from state instead of asking a
large model to search hours of video.

## Vision model vs reasoning model

WhereWatch needs a **vision-capable local model on the Pi** because the model
must inspect pendant images directly.

The vision model's job is narrow and structured. For a useful frame it should
produce something like:

```json
{
  "time": "14:17:32",
  "object": "black glasses case",
  "action": "placed",
  "location": "kitchen table",
  "relative_position": "beside coffee machine",
  "confidence": 0.94
}
```

That record is small, searchable, and can outlive the source video according
to the user's retention settings.

A huge text model or multi-node cluster can be useful during development for
experiments with ambiguous natural-language queries, but it is explicitly
**optional**. It must never become required for normal WhereWatch operation.

## Target product

```text
wall power -> Raspberry Pi

USB-C charger -> pendant battery -> wear pendant

Nothing else required.
```

If a future feature cannot run within this two-device boundary, it should be
considered an optional enhancement rather than part of the core product.
