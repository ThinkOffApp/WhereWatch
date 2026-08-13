# WhereWatch shopping list — ready to order

All links are Amazon.de, prices CHECKED Aug 13 2026 (may drift - the link is
the source of truth, not the number here). Berlin 10245, most deliver next day.
Order when petrus knows his Berlin dates (delivery is fast).

## Pendant (the wearable) — order all

| # | Part | Price | Link (ASIN) |
|---|------|------:|-------------|
| 1 | **XIAO ESP32S3 Sense** (brain: ESP32-S3, mic, microSD, USB-C batt charging, OV5640-compatible cam connector) | ~32 | amazon.de/dp/B0DRNW6KMG |
| 2 | **Borimend OV5640 for XIAO ESP32S3 Sense** (guaranteed-fit camera + 2 heat sinks) | ~34 | amazon.de/dp/B0H68Z5QZJ |
| 3 | **diymore OV5640 160° wide-angle 2-pack** (the WIDE lens petrus wants; A/B vs #2's ~70°) | ~27 | amazon.de/dp/B0H7GTLB4D |
| 4 | **GY-521 / MPU-6050 IMU 3-pack** (motion + leave-detection) | ~11 | amazon.de/dp/B0DM4NJG28 |
| 5 | **LiPo 3.7V 2100mAh protected, 6.5mm thin** (fits a chest pendant) | ~19 | amazon.de/dp/B095BRVD96 |
| 6 | **GPS: choose one** — see GPS section below | 10-28 | — |

Pendant total (with mid GPS): ~**135 EUR** (spares included: 2 cameras + 3 IMUs).

## GPS module (petrus: don't forget!) — pick ONE

For a wearable, small + UART + low power matters. Options, cheapest first:

| Option | Price | Link | Note |
|--------|------:|------|------|
| **ATGM336H GPS+BDS dual-mode** (RECOMMENDED: tiny, dual-constellation, 50+ bought/mo) | ~11 | amazon.de/dp/ (search "ATGM336H GPS BDS") | best size/perf/price for the pendant |
| GT-U7 (NEO-6M class, IPEX antenna, very small) | ~10-16 | search "GT-U7 GPS IPEX" | proven, tiny, Arduino-friendly |
| BN-180 UART GPS+GLONASS + ceramic antenna | ~28 | search "BN-180 GPS UART" | bigger, higher quality, dual-constellation |

My pick: **ATGM336H** (~11) - smallest and dual-constellation. Confirm exact
listing at order time (I'll finalize the ASIN then).

## Base station (DECIDED: mini PC, not a Pi)

| Part | Price | Link |
|------|------:|------|
| **BOSGAME E5 mini PC** — Ryzen 5300U, 16GB/512GB, complete (case+PSU+OS), boots out of box | ~299 | search "BOSGAME E5 Ryzen 5300U 16GB 512GB" (confirm COMPLETE, not barebones) |
| FAST alternative: BOSGAME P3 Pro, Ryzen 9 7940HS + Radeon 780M, 16GB/1TB | ~570 | search "BOSGAME P3 Pro 7940HS 780M" |

## Tools (buy once, if not owned)

| Part | Price | Link | Note |
|------|------:|------|------|
| USB-C soldering iron (Pinecil V2 / TS101 class) | ~40 | search "Pinecil V2" or "TS101 soldering iron" | for the XIAO battery pads; travels Berlin<->Helsinki |
| Basic kit alternative | ~20-30 | search "Lötkolben Set" | iron + stand + solder + tips |
| 0.8mm lead-free solder (if kit lacks it) | ~8 | search "0.8mm bleifrei Lötdraht" | |

## Phase-2 optional (NOT needed for v1)

| Part | Price | Link | Note |
|------|------:|------|------|
| Backlit color status display (Pimoroni Display HAT Mini or small IPS) | ~25 | search "Pimoroni Display HAT Mini" | glows in the dark; USB/HDMI on a mini PC |
| USB mic + small speaker (voice endpoint) | ~8-15 | search "USB mini microphone speaker" | |
| USB backup SSD/stick (auto-backup) | 10-40 | any | user-supplied |

## Notes

- The 3D-printed pendant case + display shroud + cradle are printed from the
  repo's OpenSCAD, no purchase (just filament, or a print service).
- v0.1 case = duct tape, which doubles as the measurement fixture for the CAD.
- I finalize the [search] links into exact ASINs the moment petrus sets a
  Berlin date, so nothing is stale at order time.
