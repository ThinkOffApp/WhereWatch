# WhereWatch — future website copy

Status: copy draft only. There is no website yet.

## Hero

### Where did I put it?

WhereWatch remembers for you.

A tiny camera pendant notices where you place everyday objects. A Raspberry Pi in your home keeps the useful stills and runs the AI locally. Ask where your keys, glasses, wallet, charger or tool went and get the last-seen place, photo and time.

**Two devices. Zero cloud.**

Plug in the Pi. Charge the pendant over USB-C. Wear it.

No subscription. No remote AI service. No account required for the core system.

Primary CTA for a future site: **See how it works**

Secondary CTA: **View the open-source project**

## Core promise

### Only you should know where your things are

WhereWatch is designed around object memory, not surveillance.

- **No video stored.** The live stream is transient processing input; only useful still images survive.
- **Faces blurred before storage.** People in retained images are scrubbed before those images enter the memory store.
- **No face identification.** WhereWatch tracks things, not people.
- **No cloud required.** Images, object history and AI inference stay on the Raspberry Pi in your home.
- **No subscription required.** The local system keeps working without a hosted service.

## How it works

### 1. Wear the pendant

The small ESP32-S3 pendant carries a wide-angle camera and battery. It captures low-rate images while you move around and sleeps aggressively when nothing useful is happening.

### 2. The Pi remembers the useful moments

The pendant sends images over Wi-Fi to your Raspberry Pi. Frigate handles the cheap video/event plumbing. A local vision model examines useful frames and records structured memories such as:

> Black glasses case — placed on kitchen table beside coffee machine — 14:17

### 3. Ask naturally

Ask:

> Where are my glasses?

WhereWatch answers from its local object-state memory with the last known place, timestamp and retained image.

Most questions do not require searching through hours of imagery or waking a huge language model. The system maintains the latest known state of each object as it goes.

## The whole system

```text
Pendant
ESP32-S3 + camera + battery
        |
        | Wi-Fi
        v
Raspberry Pi
Frigate + local vision model + object memory
        |
        v
"Where are my keys?"
```

That is the target product boundary.

A desktop GPU, M5 cluster, cloud model, NAS or other server may be useful for development experiments, but none is required for normal WhereWatch operation.

## Product highlights

### Tiny hardware

One wearable pendant. One always-on Raspberry Pi.

### Local AI

Image understanding and object-memory extraction run on hardware you control.

### Built for small objects

High-resolution stills preserve the detail needed to find keys, glasses, remotes, cables, tools and other things that conventional security-camera detectors often miss.

### Memory, not life-logging

WhereWatch is intended to retain the minimum evidence needed to answer where an object went, rather than build a permanent video archive of your life.

### Visible privacy controls

The camera should look like a camera, not a hidden recorder. Covering the lens pauses capture, and the finished hardware target includes an obvious hardware off control.

## Short launch version

**Two devices. Zero cloud.**

WhereWatch is a tiny pendant that remembers where you put things. A Raspberry Pi in your home runs the AI and stores the last useful photo of each object.

Ask "where are my keys?" and get the last-seen location, image and time.

No video stored. Faces blurred before storage. No face identification. No subscription. Your object history stays at home.

## One-line versions

**Functional:** A local-AI pendant that remembers where you left things.

**Privacy:** WhereWatch remembers your things without sending your life to the cloud.

**Minimal:** Wear it. Put things down. Ask where they went.

**Technical:** ESP32 vision pendant + Raspberry Pi object memory, fully local.

## Future page structure

When a website exists, a simple one-page launch site can use this order:

1. Hero: "Where did I put it?"
2. Immediate demo: ask for keys -> last-seen image
3. "Two devices. Zero cloud."
4. Three-step explanation
5. Privacy guarantees
6. Hardware picture / exploded view
7. Open-source status and current build stage
8. GitHub CTA

Keep the page concrete. The strongest demo is not a generic AI chat screen; it is a real object being placed somewhere, followed later by the system returning the correct image and location.
