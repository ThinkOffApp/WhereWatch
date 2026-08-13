# WhereWatch hardware — draft list

Status: DRAFT, nothing purchased or validated. Candidates marked
[verify] need a datasheet/stock check before ordering.

## Pendant

| Part | Candidate | ~Cost | Notes |
|------|-----------|-------|-------|
| Camera | **OV5640 5MP, WIDE-ANGLE lens (120-160 degree module)** | in kit or 8-12e module | DECIDED (petrus): 5MP is required, small objects need the resolution; wide angle so the pendant sees the whole scene |
| Brain board | ESP32-S3 board driving an OV5640: Freenove/LILYGO OV5640 kits, or XIAO ESP32S3 Sense with an OV5640 swap on its camera connector [verify swap compatibility] | 20-30e | Needs PSRAM for 5MP frames; battery management on-board preferred [verify per model] |
| Mic | on chosen board, else INMP441 I2S | 0-4e | trigger-only voice tags |
| IMU (leave/motion detection) | MPU-6050 breakout | 3-5e | I2C, two wires; skip if chosen board has one [verify] |
| Battery | 2000mAh 3.7V LiPo, JST-PH | 10-15e | Pick a cell that physically fits the enclosure; protected cell preferred |
| Button | 6mm momentary + cap | <1e | Tap = voice tag, double-tap = status buzz, hold = power |
| Vibration motor | coin/LRA motor + transistor | 1-3e | Haptic status: 1 buzz = on+connected, 2 = on offline, silence = off |
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
