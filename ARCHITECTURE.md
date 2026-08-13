# WhereWatch architecture

## Product constraint: only two devices

The finished WhereWatch system is deliberately just:

1. **Pendant** — ESP32-S3 + camera + battery, worn by the user.
2. **Raspberry Pi** — always-on local base station at home.

There is no required cloud service, GPU server, M5 cluster, desktop Mac, NAS,
or third appliance.

### Power and charging

Day-to-day physical setup is intentionally simple:

- **Raspberry Pi:** stays connected to its own power supply and remains online continuously.
- **Pendant:** has a separate USB-C charger; charge it, then wear it untethered.

Charging the pendant never requires unplugging or repurposing the Pi power supply.
The Pi may have an SSD attached inside/under its case, but this does not create
another user-facing device.

On first setup the Pi joins Wi-Fi and is then intended to run headless. After
that, normal use should not require a monitor, keyboard, or Ethernet cable.

### Wi-Fi commissioning

The preferred setup should require **no typing of Wi-Fi passwords into
WhereWatch**.

On Android, the user can open a saved Wi-Fi network and choose **Share** to
display the system Wi-Fi QR code. The pendant already has a camera, so the
first-run flow can be:

```text
Android phone
  Settings -> Wi-Fi -> saved network -> Share
             |
             | show QR code
             v
WhereWatch pendant camera
  decode network credentials locally
             |
             | join Wi-Fi
             |
             | securely hand credentials to paired Pi over Bluetooth
             v
Raspberry Pi
  join the same Wi-Fi
```

Google/Android may restore Wi-Fi credentials between Android devices, but
WhereWatch should not depend on access to Google's private saved-credential
store. The QR share flow uses the user's existing Android UI instead and
keeps commissioning local.

The Pi and pendant should be paired as a kit. For prototypes this can use a
one-time pairing code or first-run physical pairing; a production device can
ship with per-device credentials/certificates so that Wi-Fi credentials are
only accepted by the matching Pi.

Fallback setup options:

- temporary BLE provisioning from the WhereWatch phone UI;
- temporary Pi setup access point / local web page;
- manual SSID/password entry;
- preconfiguration for developer images.

The normal user path remains: **show one QR code, then use the system.**

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
  face blur (every stored image is scrubbed BEFORE it touches disk)
        |
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
- keep snapshots (clip retention stays OFF: WhereWatch stores stills only,
  never video - the stream is transient plumbing, not a recording);
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

## Location: wifi first, GPS as the away-from-home add-on

The pendant has no GPS chip and mostly does not need one. Location comes in
layers, cheapest first:

1. **Wifi fingerprint (free, already on board):** with every batch of frames
   the pendant includes the BSSIDs/RSSI it can hear. The Pi learns named
   places ("home", "office", "cafe") and - with a short calibration walk -
   even rooms ("kitchen" vs "hallway"), fully locally.
2. **Vision context (free):** the model's location field ("kitchen table")
   already names the spot inside a known place.
3. **GPS (optional part, ~5-10e):** a small GNSS module on the pendant's
   spare UART covers placements away from any known wifi - the parked car,
   the beach bag. Coordinates are stored locally like every other
   observation. Optional enhancement, not core.

### Map view

The web app gains a map tab: your things as pins, each pin the last-seen
photo + timestamp. Indoor placements cluster on the named place; away-from-
home placements (GPS or unknown-wifi) drop pins on the map. Map tiles are
fetched by the viewing browser; placement data never leaves the Pi.

## Target product

```text
Pi power supply -> Raspberry Pi (always on)

separate USB-C charger -> pendant battery -> wear pendant

Nothing else required.
```

If a future feature cannot run within this two-device boundary, it should be
considered an optional enhancement rather than part of the core product.
