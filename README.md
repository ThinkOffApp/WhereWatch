# WhereWatch

**A pendant that remembers where you left things — fully local.** A tiny
wearable camera photo-logs your day into a Raspberry Pi at home; a local
vision model watches the trail. Ask *"where are my keys?"* and get back the
last photo that contains them, with a timestamp. No cloud, no subscription,
nothing leaves your house.

Sibling of [CarWatch](https://github.com/ThinkOffApp/CarWatch) (your car as a
team-chat agent), [ClawWatch](https://github.com/ThinkOffApp/ClawWatch)
(health on your wrist) and [CodeWatch](https://codewatch.app) (your agents on
your phone). This one watches where things went.

## Status — honesty first

**Design stage. Nothing here is built yet.** This README is the agreed
design; code lands as it is written and every feature will be labeled
*proven / built + tested / planned*, the same policy as CarWatch.

## The design

### Pendant (ESP32-S3 + OV5640 camera + 2Ah battery)

Hardware philosophy: minimal. **One button** (tap: voice tag, double-tap:
status check, hold: power), **one USB-C port** (charging, and wired transfer
as an offline option), a **tiny vibration motor** as the only output, no
screen, no LED. Covering the lens is the pause control.

Haptic status (double-tap the button): one buzz = on and connected, two
buzzes = on but offline, silence = off. The whole UI in your fingertips.


One device, two appetites, switching automatically by battery state:

| Mode | When | What | Battery |
|------|------|------|---------|
| Stream | charging or battery healthy | low-res MJPEG at 2 fps over wifi | ~5–8 h est. |
| Stills | below battery threshold | one photo every 20–30 s, deep sleep between | a full day+ |

Camera: **OV5640, 5 MP, wide-angle lens** — small objects need the pixels.
Dual-pipe capture: the 2 fps stream runs low-res (Frigate only needs motion),
while the frames that get indexed are full 5 MP stills, so "keys on a
cluttered table" survives with readable detail without spending battery on
5 MP video.

**Motion-gated transmission (battery multiplier):** the pendant only
transmits when something is actually happening. Two triggers, cheapest first:
on-device frame differencing (compare consecutive low-res frames, no extra
part needed) and optionally a tiny IMU (movement of the wearer). Still scene,
still wearer = radio off, deep sleep. Wifi transmit is the power hog, so
motion gating stretches every battery estimate above substantially.

### Base station (any Raspberry Pi–class box)

- **Cheap filter:** [Frigate](https://frigate.video) ingests the 2 fps
  stream and flags motion / person / object events — near-zero cost.
- **Expensive brain:** a local vision-language model (Qwen3.6-class with an
  mmproj projector, the same stack CarWatch runs) wakes only for flagged
  frames and all stills, captioning and inventorying each into a small index:
  *objects seen, where, when*.
- **The question:** "where are my keys" is a text search over the captions,
  answered with the newest matching photo and its timestamp — in your team
  chat, like every other agent in the family.

**Lens-cover pause:** covering the camera IS the pause button - a run of
all-dark frames stops capture and transmission until light returns. A
physical privacy gesture anyone in the room can see and perform, no app
needed.

**Voice tags ("leaving my keys here"):** the pendant carries a mic used ONLY
on explicit trigger - a button press or an on-device wake word (ESP32-S3
runs wake-word detection locally) - never ambient recording, the audio
equivalent of things-not-people. A short clip travels to the base station,
whisper transcribes it locally (the same stack the car uses), and the text
is pinned to that moment's photo and place in the index. Saying where you
put something beats hoping the camera noticed.

### Interfaces (the family pattern: the agent is the front door)

- **Room agent:** WhereWatch joins your team rooms like its siblings - ask
  `@wherewatch where are my keys` from anywhere and it answers with the last
  matching photo and timestamp. Proactive too: it can post "keys last seen on
  the hallway table" when you leave home without them.
- **Watch app:** one screen, one question - speak or pick a recent object,
  get the photo on your wrist. The ClawWatch/CodeWatch wrist pattern.
- **Web app:** browse the captioned timeline, search history, manage
  retention and delete days - the place for anything bigger than a glance.

## The privacy line, drawn before the first commit

**Things, not people - by design, in this branch.** WhereWatch indexes
OBJECTS only: the captioning prompt and the index schema have no notion of
who was in frame, person-class detections are dropped rather than stored,
and "where is Anna" is a question this system is built to be unable to
answer. That is a product decision, not a missing feature.

A wearable camera still photographs everyone around you, not just your keys.
WhereWatch is local-only by design — frames never leave your own hardware —
but that does not answer where wearing it is welcome. Decide that before
building the habit. The default firmware will ship with a physically obvious
lens (no hidden-camera styling) and a hardware off switch.

## Hardware

Draft parts list with candidates and open questions: [HARDWARE.md](HARDWARE.md).

## License

AGPL-3.0, like its siblings. Copyright (C) 2026 ThinkOff / Petrus Pennanen.
