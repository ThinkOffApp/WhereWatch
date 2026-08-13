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

One device, two appetites, switching automatically by battery state:

| Mode | When | What | Battery |
|------|------|------|---------|
| Stream | charging or battery healthy | low-res MJPEG at 2 fps over wifi | ~5–8 h est. |
| Stills | below battery threshold | one photo every 20–30 s, deep sleep between | a full day+ |

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

## The privacy line, drawn before the first commit

A wearable camera photographs everyone around you, not just your keys.
WhereWatch is local-only by design — frames never leave your own hardware —
but that does not answer where wearing it is welcome. Decide that before
building the habit. The default firmware will ship with a physically obvious
lens (no hidden-camera styling) and a hardware off switch.

## License

AGPL-3.0, like its siblings. Copyright (C) 2026 ThinkOff / Petrus Pennanen.
