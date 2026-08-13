# WhereWatch hardware — parts list

Parts and choices only. Costs, links, and the order list live in a private
BOM (not in this public repo). Items marked [verify] need a datasheet/fit
check before ordering.

## Pendant

| Part | Choice | Notes |
|------|--------|-------|
| Brain board | **Seeed XIAO ESP32S3 Sense** (PICKED) | thumb-sized: ESP32-S3, PDM mic, microSD, USB-C with on-board LiPo charging; detachable camera connector is OV5640-compatible (Seeed listing) |
| Camera | **OV5640, 5MP, wide-angle** (DECIDED, petrus) | 5MP required for small objects; wide angle to see the whole scene. Fit options: a XIAO-specific OV5640 module, or a generic 120-160° OV5640 (verify the XIAO connector) |
| Mic | on the XIAO, else INMP441 I2S | trigger-only voice tags |
| IMU | MPU-6050 / GY-521 breakout | motion + leave-detection; I2C, two wires |
| Battery | 3.7V ~2000-2100mAh LiPo, **protected**, thin (~6.5mm) | must physically fit the pendant; protected cell only |
| Button | 6mm momentary | tap = voice tag, double-tap = status buzz, hold = power |
| Vibration motor | coin/LRA + transistor + flyback diode | haptic status: 1 buzz on+connected, 2 offline, silence off |
| GPS (optional) | small UART GNSS (e.g. ATGM336H) | away-from-home location; on the spare UART |
| USB-C | on the board | charging + wired transfer |
| Enclosure | 3D print (OpenSCAD in cad/) | obvious-lens styling; lens/button/USB cut-outs; lanyard loop |

## Power electronics

Goal: ZERO separate power boards — the XIAO has the charge IC, protection,
3.3V rail and battery pads on board. Chain: USB-C → on-board charger →
protected LiPo → on-board 3.3V. Battery voltage read on an ADC pin for the
low-battery mode switch + honest haptic status. Only if a chosen board lacks
battery management: add a TP4056 USB-C charge/protection module.

## Base station (DECIDED: mini PC, not a Pi)

| Part | Choice | Notes |
|------|--------|-------|
| Compute | **16GB/512GB x86 mini PC** (complete unit, boots out of box) | runs Frigate + the local vision model; faster than a Pi for the encoder (threads + AVX2 + dual-channel). A Radeon 780M box is the faster upgrade for vision. Pi only if you want GPIO pins |
| Storage | NVMe SSD, 256GB min / 512GB recommended | photos + DB; SSD not SD (constant writes wear SD out). ~1-2GB/day of stills before pruning |
| Display (optional, phase-2) | backlit color IPS (glows in the dark) OR detachable e-ink Badger | status face; on a mini PC via USB/HDMI |
| Mic + speaker (optional, phase-2) | USB mic + small speaker | hands-free "where are my keys", spoken alerts |

## Tools

- USB-C soldering iron (travels well) for the XIAO battery pads — the one
  solder joint the build needs.
- Lead-free solder if the kit lacks it.

## Open questions

1. Confirm the exact OV5640 module mates with the XIAO's camera connector.
2. Wake-word (ESP-SR) RAM budget on the XIAO alongside camera + wifi [verify].
3. Battery life: all estimates get replaced by a measured number once the
   first prototype runs.
