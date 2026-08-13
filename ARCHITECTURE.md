# WhereWatch architecture

## Product constraint: only two devices

The finished WhereWatch system is deliberately just:

1. **Pendant** — ESP32-S3 + camera + battery, worn by the user.
2. **Raspberry Pi** — always-on local base station at home.

There is no required cloud service, GPU server, M5 cluster, desktop Mac, NAS,
or third appliance.

### DECIDED base: a 16GB/512GB x86 mini PC (not a Pi)

Aug 13 (petrus): the base station is a complete 16GB/512GB x86 mini PC
(BOSGAME E5, Ryzen 5300U, ~299 checked) - cheaper and faster for vision than
a 16GB Pi kit (~373), and no assembly. Accessories (status display, mic) hang
off USB instead of GPIO. The dock/charge notes below apply to whichever box;
the mini PC's USB-A ports charge the pendant the same way.

### The Pi doubles as the pendant's dock

The Pi's USB-A ports output 5V, so a USB-A-to-C cable from the Pi charges
the pendant - the base station literally becomes the charging dock. Rest the
pendant by the Pi overnight and three things happen on one cable: it charges,
it can do a full wired sync of any buffered stills, and it sits in a known
"home/charging" state the app can show. One object on the shelf, no separate
charger brick needed.

Power note: a Pi 5 on a proper 27W USB-C supply has headroom on its USB
ports for a small pendant draw (a few hundred mA); the Pi's own USB-C port
stays its power INPUT, charging goes out over USB-A. If a user runs a very
power-hungry setup, a plain phone charger still works as the fallback - the
pendant charges from any USB-C source, the dock is a convenience not a
requirement.

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

### First-run sequence (pre-paired kit)

For a kit we assembled and paired at the bench, the buyer's entire setup is:

1. Power the base (mini PC or Pi).
2. Rest the pendant on its dock/cradle - it charges and its camera faces out.
3. On the phone: open the home wifi network, tap Share, show the wifi QR.
4. Hold the phone to the pendant camera. The pendant decodes the credentials
   locally, joins wifi, and passes them to the base over the pre-paired
   encrypted link. The base joins the same network.

No keyboard, no typed password, no account. The one secret that must never
be preset - the wifi password - is exactly the step the buyer performs, so a
fully pre-assembled kit is safe to ship. The pendant needs a little charge to
scan, which the dock supplies, so the order is: power base, pendant on dock,
scan.

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

**Two display concepts, and they split cleanly by technology:**

- **Fixed backlit color face** (e.g. Display HAT Mini) - best for a base that
  sits in a dark spot, glows, shows the color status + heart. Stays on the box.
- **Detachable e-ink Badger** (petrus) - a battery + buttons e-ink board that
  DOCKS as the status face and DETACHES to carry: e-ink holds its image with
  zero power for days, so it is a perfect little take-with-you message board
  ("back in 5", a note on the door, a greeting, today's object count frozen
  on it). Docked it shows live status; undocked it keeps the last screen and
  its buttons cycle saved messages.

Messages: you write your own in the web app (a little text field -> pushed to
the Badger), OR the app suggests ones - both canned ("Back in 5", "Do not
disturb", "Welcome home") and context-aware from the index ("last home 2h
ago", "3 things left today", "remember: keys on the hall table"). The local
model can even draft a friendly line on request. Write-your-own plus
suggest-for-you, your pick. The Badger can also show PICTURES, not just text: pick a few favorite objects and it displays their auto-generated thumbnails (e-ink renders the index photo in grayscale), so a glance at the carried Badger shows "keys, wallet, glasses" as little pictures. Petrus drafts a starter set of on-brand text messages.

They are not mutually exclusive - a buyer could have the color face on the
base AND a Badger as a carry accessory - but for most, pick one: color if the
base lives in the dark, Badger if the "detach and show a message" charm wins.
E-ink is not backlit, so a Badger in a dark room is not glanceable; that is the
one honest trade.


A small display on the Pi gives it a calm, glanceable face - "pendant 72%,
streaming", "storage 38% used (~5 months left)", "backup complete, safe to
remove", "last event 2 min ago", today's object count - no interaction, no
cloud, just proof it is alive and healthy. The two most useful lines are
pendant charge and storage headroom. The display THEME matches your device
color (a lime pendant = lime accents), and on any non-black variant it shows
the ThinkOff heart, so the base station wears the same color as the pendant. Recommended pick: a small **e-ink** panel (Pimoroni Badger-class or
an e-ink HAT). E-ink holds its text with the Pi asleep, sips no power, and
suits an always-on home object better than a glowing screen; a colour TFT is
a fine alternative if you prefer livelier status. This is the add-on to reach
for before the mic/speaker. Still phase-2, still optional.

The Pi uses a stock off-the-shelf case (no custom enclosure). The only
printed parts are small OPTIONAL accessories, both parametric OpenSCAD in
this repo alongside the pendant case:

- a **display shroud** that clips onto the stock case and holds the e-ink/TFT
  panel at a readable angle (instead of bare-gluing it), and
- a **pendant cradle** - a little dock pocket that holds the pendant against
  its charging cable so "set it down by the Pi" has an actual resting spot.

They can be one combined clip-on piece: display up top, cradle below, the
charge cable routed through. Print-optional; the product works without them
(glue the display, rest the pendant anywhere), they are just the tidy
finishing touch for whoever has a printer.

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

**Scan notifies the owner (found-mode).** When the return page is opened,
it can ping you - "your WhereWatch was just scanned" - straight to your
room/CodeWatch, so you know it has been found and can arrange pickup. Two
honest constraints keep this a recovery aid, not a tracker:

- **Finder transparency:** the page says plainly that scanning notifies the
  owner, and any location share is an explicit finder tap ("share my
  location to help return this"), never silent GPS/IP geolocation. This is
  the AirTag/Tile found-mode norm, and the anti-stalking reason for it
  applies to us too.
- **Minimal + owner-routed:** the scan event carries only what the finder
  chose (a note, an opted-in coarse location); it routes to the OWNER, and
  nothing about the finder is retained after the item is recovered. The
  return host holds a contact card and a notify hook, never the memory DB.

The nice symmetry stays intact - the device that helps you find things is
itself findable and returnable - without the QR ever becoming a data leak or
a way to track whoever picked it up.

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
  tiles are the documented recommended setup. **We never use Google Maps** -
  a Google (or any hosted) tile/JS overlay sends the map viewport to that
  provider, which reveals roughly where your things are and breaks the
  no-cloud promise. The map uses OpenStreetMap tiles either bundled offline
  for your area or proxied+cached through the Pi, so the browser never talks
  to a tile CDN directly. Default stays the tile-free place-cluster view.
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

## Storage: how much, how long

The base's SSD holds the stills + the tiny DB. Rough math:

- A face-blurred 5MP JPEG is ~1-2 MB. WhereWatch does NOT keep every frame -
  motion-gating + dedup means it keeps a still when something actually
  changes/places, ballpark a few hundred to ~1-2k keeper stills a day.
- That is ~0.5-2 GB/day of photos. The episode DB itself (rows + FTS index)
  is trivial - megabytes even over a year; text is cheap, pixels are not.

So a **256 GB SSD** holds roughly **4-12 months** of full-photo history
before retention prunes anything, and a **512 GB** doubles that. With a
30-day retention window you would only ever use ~15-60 GB. RAM (16 GB) is for
running the vision model + Frigate, not storage - the two are separate: 16 GB
memory, 256-512 GB disk. Plenty of headroom; the display just shows the used
percentage so you are never surprised.

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
