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

## The Pi as a voice point (mic + speaker)

A small USB/I2S mic and speaker on the Pi make the home base a hands-free
endpoint, not just a web server:

- **Ask out loud:** "where are my keys?" answered by voice from the same
  index the web app uses - the eyes-free path for exactly the moment you are
  looking for something and your phone is the thing you cannot find.
- **Wake word runs locally** (the CarWatch voice stack already does this on
  a Pi); audio is processed on-device and NOT stored - voice follows the
  same things-not-people rule, transcribe-and-discard, never a recording.
- **Spoken confirmations:** "backup done", "pendant battery low", "front
  door not seen since you left" - the Pi can speak the proactive alerts the
  web app would otherwise only show.
- **Told-not-seen by voice:** "remember I put my passport in the car" spoken
  to the Pi writes a note episode (source=voice), same as saying it to the
  pendant.

### Optional ambient status face (phase-2)

A small display on the Pi gives it a calm, glanceable face - "pendant 72%,
streaming", "backup complete, safe to remove", "last event 2 min ago",
today's object count - no interaction, no cloud, just proof it is alive and
healthy. Recommended pick: a small **e-ink** panel (Pimoroni Badger-class or
an e-ink HAT). E-ink holds its text with the Pi asleep, sips no power, and
suits an always-on home object better than a glowing screen; a colour TFT is
a fine alternative if you prefer livelier status. This is the add-on to reach
for before the mic/speaker. Still phase-2, still optional.

The Pi uses a stock off-the-shelf case (no custom enclosure - only the
PENDANT gets the printed OpenSCAD case). A status display just glues or
sticks to the outside and connects to the header; nothing to design.

Strictly optional, phase-2 hardware - NOT part of the first build. The web
app and pendant are the product; voice is an add-on for whoever wants it.
The two-device boundary holds because the mic and speaker live inside the Pi
box, not as a third device. Backups work fully without a speaker (a status
line in the web app and a note in the room); the spoken "backup complete" is
just a nicety when the speaker is present.

## The pendant's printed QR (two purposes, kept apart)

The pendant carries a small printed QR. It is tempting to make it "the
dashboard link", but a lost-and-found device that is itself lost must not
hand a finder the keys to your home memory. So the QR is finder-safe by
default and never the private dashboard:

- **Printed on the pendant = the RETURN page.** Scanning it opens a small
  public "you found someone's WhereWatch" page served... not from your Pi
  (your Pi is not on the public internet). It shows only what you chose to
  put there: "please return to" contact (a phone/email/alias you set), an
  optional reward note, and how to power it down. ZERO access to your data,
  your dashboard, your home. A stranger scanning it learns how to give it
  back, nothing else.
- **Your dashboard is reached separately** and stays private: the phone you
  already paired opens it on your home network (or your own VPN). It is
  auth-gated and LAN-scoped per the security section; it is never behind a
  QR a finder could scan.
- Implementation: the return page is a static owner-authored card. Simplest
  privacy-preserving hosting is a self-chosen URL (or a plain printed "return
  to <your contact>" with no URL at all). The pendant's own identity is a
  random token that maps to the contact card only, never to the memory DB.

The nice symmetry stays intact - the device that helps you find things is
itself findable and returnable - without the QR ever becoming a data leak.

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

## The index is episodic memory (WhereWatch is one view of it)

The observation record was designed for placements, but nothing in it is
placement-specific. Generalized, the Pi keeps ONE small episodic-event table
with an event kind:

- `placement` - object seen/placed somewhere (the Where view)
- `state` - door locked, stove off, window closed (the Did I view)
- `action` - watered plants, fed the cat, took medication
- `departure` - what left the house with you (possession checks)

Question families map onto the same table: Where / Did I / State / Action /
Possession ("did I take my wallet when I left") / Sequence ("what did I do
after I came home" = a time-range query). WhereWatch and DidIWatch are tabs
over one memory, not separate systems.

The privacy rules apply to the WHOLE table, harder as it broadens: things
and states, never people; face-blur before storage; sequence answers list
object/state events only; retention deletes episodes wholesale. An episodic
memory of your home must be even more obviously yours-only than a keys
finder, which is why the two-device, no-cloud boundary is non-negotiable.

## The database

**SQLite, one file on the Pi.** Zero administration, survives power loss,
trivially backed up by copying one file, and its FTS5 full-text index makes
caption search instant. On a Pi-scale write load (a few events per minute at
worst) it is the boring, correct choice. No server, no ORM.

```sql
CREATE TABLE episode (
  id          INTEGER PRIMARY KEY,
  ts          TEXT NOT NULL,              -- ISO time
  kind        TEXT NOT NULL,              -- placement|state|action|departure|note
  object      TEXT NOT NULL,              -- "keys", "front door", "plants"
  verb        TEXT NOT NULL,              -- placed|seen|locked|watered|left-with
  place       TEXT,                       -- "kitchen table" (vision or wifi)
  rel_pos     TEXT,                       -- "beside coffee machine"
  wifi_place  TEXT,                       -- fingerprint-derived place name
  lat, lon    REAL,                       -- only when GPS module present
  photo_path  TEXT,                       -- Pi-local still (face-blurred)
  source      TEXT NOT NULL,              -- vision|voice|chat|button
  confidence  REAL
);
CREATE VIRTUAL TABLE episode_fts USING fts5(object, verb, place, rel_pos,
  content=episode, content_rowid=id);
-- external-content FTS needs the sync triggers or it silently drifts:
CREATE TRIGGER episode_ai AFTER INSERT ON episode BEGIN
  INSERT INTO episode_fts(rowid, object, verb, place, rel_pos)
  VALUES (new.id, new.object, new.verb, new.place, new.rel_pos); END;
CREATE TRIGGER episode_ad AFTER DELETE ON episode BEGIN
  INSERT INTO episode_fts(episode_fts, rowid, object, verb, place, rel_pos)
  VALUES ('delete', old.id, old.object, old.verb, old.place, old.rel_pos); END;
CREATE TRIGGER episode_au AFTER UPDATE ON episode BEGIN
  INSERT INTO episode_fts(episode_fts, rowid, object, verb, place, rel_pos)
  VALUES ('delete', old.id, old.object, old.verb, old.place, old.rel_pos);
  INSERT INTO episode_fts(rowid, object, verb, place, rel_pos)
  VALUES (new.id, new.object, new.verb, new.place, new.rel_pos); END;

CREATE TABLE current_state (              -- the fast answers, per question
  object      TEXT NOT NULL,              -- "keys" / "keys#2" for instances
  kind        TEXT NOT NULL,              -- placement|state|action|departure
  episode_id  INTEGER REFERENCES episode(id),
  PRIMARY KEY (object, kind)
);
```

Event kinds: placement | state | action | departure | note (told-not-seen
rows are kind=note with the verb carrying the claim).

Deterministic answer rule, in order: (1) higher source rank wins - note
sources (voice/chat/button) rank above vision; (2) then newer ts; (3) then
higher confidence; ties broken by id. One query, no heuristics at read time.

Multiple instances of a thing ("keys" vs the spare set) get instance-suffixed
object names at ingest; current_state's (object, kind) key answers state and
placement questions independently.

Every question family is one query: Where = current_state(object, placement);
Did I = current_state(object, state|action) filtered to today; Sequence =
time-range scan over episode. Retention is one DELETE older than N days plus
unlinking the photos (and the FTS delete-trigger keeps the index honest).

## Privacy hardening (codex review, Aug 13)

- **Fail-closed face blur:** no frame reaches ANY durable write until the
  blur stage reports success; blur failure or low-confidence person
  detection = frame dropped, counted, never stored. The gate covers every
  write path: Frigate snapshots and clips (recording and disk snapshots
  explicitly disabled in Frigate config), thumbnails, model caches, logs,
  crash dumps, backups. Person detection is treated as imperfect - the
  pipeline errs toward dropping.
- **External posting is opt-in, per question family.** The room agent
  answers in-room only if the owner enabled it; default is web-app-only.
  A posted answer is a location disclosure and the setting says so.
- **Map tiles disclose metadata:** fetching tiles tells the provider roughly
  where you are. The map view defaults to the place-cluster view (no tiles);
  turning on the tile map shows a one-time notice, and self-hosted/offline
  tiles are the documented recommended setup.
- **Wifi fingerprints are location identifiers:** BSSIDs are stored as
  installation-scoped salted hashes, never shown in the UI, never exported.
  Weak RSSI evidence returns "unknown", not a guess; room-level accuracy is
  a calibration promise to MEASURE, not assume (RSSI alone may only manage
  place-level). AP rotation (BSSID churn) triggers re-calibration hints.
- **GNSS handling:** no-fix and stale-fix produce no coordinates (never a
  last-known silently reused); fixes carry accuracy metadata; GPS rows
  follow the same retention as photos; leaving home with no known wifi and
  no GNSS module = honest "away, location unknown".
- **"No video stored" is an acceptance test,** not a slogan: the test suite
  asserts no container/stream files exist on disk after a stream session.
- **Pendant-to-Pi commissioning:** paired kit with per-device secret;
  frames are authenticated (HMAC) and the channel encrypted; replayed
  frames are rejected by timestamp+nonce.

## Pi security: hardened by default, hack-tested before shipping

The Pi holds an episodic memory of a home - a high-value target, so the
threat model is written down and TESTED, not assumed.

Baseline hardening (ships as the default image):
- Web UI binds to LAN only; no port forwarding, no UPnP, nothing listens on
  WAN. Remote access, if ever offered, is opt-in via the owner's own VPN.
- The web app requires auth (per-device pairing token on first visit; no
  default passwords anywhere; SSH key-only and disabled by default in the
  consumer image).
- Every service runs as an unprivileged user; systemd sandboxing
  (ProtectSystem, PrivateTmp, NoNewPrivileges) on all WhereWatch units.
- Unattended security updates on; the WhereWatch updater is signed.
- Encryption at rest for photos + DB (the SD card walking away must not mean
  the memory walks away readable) - LUKS or per-file, decided by measured Pi
  overhead.
- Pendant link: HMAC-authenticated, encrypted, replay-rejected (above).

Hack-test plan (every release, on a real device):
1. Surface scan: nmap TCP/UDP from LAN and WAN side; anything unexpected
   open = release blocker.
2. Web/API: auth bypass and fuzzing on every /api/* endpoint, IDOR on photo
   paths, CSRF on retention/settings, rate limiting on ask.
3. Commissioning: replay and evil-twin attempts against the QR/BLE pairing;
   a stolen pairing QR must not grant a second device access.
4. Physical: pull the SD card, verify photos/DB unreadable; boot tamper.
5. Update channel: attempt unsigned/downgraded update installation.
Findings get filed as issues in this repo and block the release until fixed.

## Sole holder: the concentration is the feature, and the risk

The Pi is the ONLY copy of your home's memory. That is the whole privacy
guarantee - no cloud copy means no cloud breach, no vendor subpoena, no
account to leak. But sole-holder means one box carries two risks, and the
design must answer both honestly:

- **Compromise (someone gets the box/card):** encryption at rest is the
  answer - a stolen SD card is ciphertext, not your life. Covered in the
  security section; the key is derived from an owner secret set at
  commissioning, not stored in the clear on the card.
- **Loss (the Pi dies, the card corrupts):** sole-holder must not mean
  single-point-of-loss. The design's answer is **local, encrypted,
  owner-controlled backup** - to a USB SSD in the same case, or to another
  device the owner already has at home (a NAS, a second Pi), never to a
  cloud by default. Backups carry the same encryption and retention as the
  live DB. An optional owner-initiated encrypted export (a file the user
  holds) covers "I want a copy off-site" without WhereWatch ever choosing a
  third party for them.
  - **Plug-in auto-backup:** insert a USB stick/SSD and the Pi backs up to
    it automatically - a udev rule fires on insert, the drive is recognized
    by a WhereWatch marker, an encrypted incremental snapshot is written,
    and the speaker says "backup done, safe to remove". First-time inserts
    prompt for one-tap enrolment (so a random stranger's stick is not
    trusted). Pull it, put it in a drawer: that is your off-site copy, still
    encrypted, still only openable with your secret.

The principle: WhereWatch never widens the trust boundary to solve
reliability. Redundancy stays inside the home and inside the owner's
control, or it does not happen.

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
