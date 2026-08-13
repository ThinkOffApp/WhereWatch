# WhereWatch hardware — draft list

Status: DRAFT, nothing purchased or validated. Candidates marked
[verify] need a datasheet/stock check before ordering.

## Pendant

| Part | Candidate | ~Cost | Notes |
|------|-----------|-------|-------|
| Brain + camera + mic | **Seeed XIAO ESP32S3 Sense** | 20-25e | Smallest pendant-able board: ESP32-S3, camera, PDM mic, microSD, battery pads with built-in LiPo charging over USB-C. Camera is OV2640 (2MP), not OV5640 [verify: is 2MP enough at 2fps low-res? probably yes] |
| Alt board (OV5640) | Freenove/LILYGO ESP32-S3 cam kits with OV5640 | 20-30e | True 5MP per the original idea, but physically larger and some lack battery management [verify per model] |
| IMU (leave/motion detection) | MPU-6050 breakout | 3-5e | I2C, two wires; skip if chosen board has one [verify] |
| Battery | 2000mAh 3.7V LiPo, JST-PH | 10-15e | Pick a cell that physically fits the enclosure; protected cell preferred |
| Button | 6mm momentary + cap | <1e | Tap = voice tag, hold = power |
| USB-C | on the board | - | Charging + wired transfer |
| Enclosure | 3D print | ~2e material | Obvious-lens styling per README; lanyard loop; button cutout |
| Lanyard | any | 2-5e | |

Pendant total: roughly 40-55e.

## Base station

| Part | Candidate | Notes |
|------|-----------|-------|
| Compute | any existing always-on box: a Pi 5, the home server, or the Bosgame-class machine | Frigate (2fps stream is a trivial load) + the vision model (Qwen3.6-class + mmproj) |
| Storage | whatever the box has; ~1-2GB/day at 2fps low-res before pruning | Retention policy lives in the web app |

No new base-station purchase needed if a fleet machine is already running.

## Consumables / tools

- USB-C cable (owned)
- Soldering only if the IMU breakout is added; the XIAO route can be solder-free except battery pads [verify]

## Open hardware questions

1. OV2640 (tiny board, built-in everything) vs OV5640 (sharper, bulkier): decide after a resolution test on sample frames.
2. Wake-word on ESP32-S3 (ESP-SR) RAM budget alongside camera + wifi [verify on chosen board].
3. Battery life measurements replace all estimates once the first prototype runs.
