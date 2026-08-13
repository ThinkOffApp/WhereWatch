# WhereWatch

**A pendant that remembers where you left things — fully local.** A tiny
wearable camera photo-logs your day into a Raspberry Pi at home; a local
vision model watches the trail. Ask *"where are my keys?"* and get back the
last photo that contains them, with a timestamp. No cloud, no subscription,
nothing leaves your house.

## Two devices. Zero cloud.

Plug in the Raspberry Pi. Charge the pendant over USB-C. Wear it.
That is the whole system.

WhereWatch remembers where you placed your things, privately. The Pi stores
a photo of the last useful observation of an item, together with its time and
location. If people appear in a retained image, faces are blurred before that
image becomes part of the memory store.

- **No cloud service required**
- **No subscription required**
- **No video stored**
- **No face identification**
- **Faces blurred before retained images are written to storage**
- **Object-location history stays on the Pi in your home**

The product target is deliberately small: **pendant + Raspberry Pi**. A large
GPU box, desktop, NAS, M5 cluster, or hosted AI service may be useful for
experiments, but none is part of the required product architecture.

Sibling of [CarWatch](https://github.com/ThinkOffApp/CarWatch) (your car as a
team-chat agent), [ClawWatch](https://github.com/ThinkOffApp/ClawWatch)
(health on your wrist) and [CodeWatch](https://codewatch.app) (your agents on
your phone). This one watches where things went.

## Status — honesty first

**Design stage. Nothing here is built yet.** This README is the agreed
design; code lands as it is written and every feature will be labeled
*proven / built + tested / planned*, the same policy as CarWatch.

## The product principle

**Two objects, simple power.** The whole system is a pendant you wear and a Pi
box. The Pi stays plugged into power; the pendant charges over USB-C and runs
untethered. No monitor, no keyboard, no ethernet - the box joins wifi,
self-installs, self-updates (the CarWatch pattern), and everything you ever
touch is the pendant, the room agent, and the web page the box serves.

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

**Faces are blurred before storage.** Any face in a frame is scrubbed on the
Pi before the image touches disk - the stored history physically cannot
identify people. And **no video is ever stored**: the pendant's stream is
transient plumbing for motion detection; only stills survive.

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

## Beyond "where are my keys" — same two boxes, more memory

The object-state memory answers more than lost-and-found, all local, no new
hardware:

- **Told, not seen:** say "leaving my keys here" (pendant button/wake word),
  type a note in the room chat ("note: passport is in the car"), or press the
  button - all three write the same observation record the camera would have.
  Your word outranks the camera's guess.
- **"Did I…?" checks:** did I lock the door, turn off the stove, take the
  medication, water the plants - the trail holds the last photo of the
  action, so the answer is a picture, not anxiety.
- **Running low:** the pantry/fridge shots know when the milk was last seen;
  a shopping hint falls out of the same index.
- **Before/after:** "what did the desk look like on Monday" - placement
  history doubles as a room diary.
- **Arrivals:** parcels, deliveries, things that appeared rather than moved.

Every one of these is a query over the SAME captioned-stills index; none
breaks the two-device boundary or the things-not-people rule.

## The emoji language

WhereWatch speaks in emoji - a friendly, wordless icon set that works on the
tiny display, in the app, and embossed on the case itself:

- **Objects:** 🔑 keys · 👛 wallet · 📱 phone · 🕶️ glasses · 🎧 headphones · 📕 docs · 🔋 battery
- **Location:** 📍 where it was last seen
- **Privacy promises, as a badge set:** 🎥🚫 no video · 🙈 no faces · ☁️🚫 no cloud

The privacy trio can be embossed right on the case as a wordless promise
anyone can read at a glance, and the same emoji tag each object in the app and
on the carried Badger. One little visual language across plastic, screen, and
software.

### Colorways + covers

Shell in **Black + four ThinkOff colors** (Fuchsia #D946EF, Orange #F97316,
Yellow #FACC15, Lime #84CC16), soft-touch finish. Your chosen color also
themes the web app accent.

Optional slip-on **covers** over the shell:
- **Soft silicone skin** - grippy, drop-protective, wipes clean.
- **Furry/plush cover** - the playful option. Cut-outs for the lens, button
  and USB-C. On-brand fun, and it makes the camera friendly and obviously a
  camera - the opposite of a hidden spy device, which fits the things-not-
  people ethos. Covers must never occlude the lens, mic port, or charge port.

## Hardware

Draft parts list with candidates and open questions: [HARDWARE.md](HARDWARE.md).

Architecture and the strict pendant + Pi boundary: [ARCHITECTURE.md](ARCHITECTURE.md).

Future website/launch copy: [WEBSITE_COPY.md](WEBSITE_COPY.md).

## License

AGPL-3.0, like its siblings. Copyright (C) 2026 ThinkOff / Petrus Pennanen.
