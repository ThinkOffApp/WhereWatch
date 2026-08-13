# WhereWatch cost + pricing notes

All figures EUR. Two columns: **retail** = what you pay buying ONE of each
part today (the prototype cost), **volume** = rough BOM if built in hundreds+
(what pricing math should use). Prototype prices are from the Aug 2026
Amazon.de shopping pass; volume numbers are estimates, not quotes.

## Pendant (the wearable)

| Part | Retail (1 off) | Volume est. |
|------|---------------:|------------:|
| XIAO ESP32S3 Sense board | 32 | 14 |
| OV5640 wide-angle camera module | 15 | 6 |
| IMU (GY-521 / MPU-6050) | 4 | 1.5 |
| LiPo 2000-2100mAh, protected | 15 | 4 |
| Button + vibration motor + wiring | 3 | 1 |
| Printed enclosure (filament) | 2 | 1 |
| **Pendant subtotal** | **~71** | **~28** |

## Base station (the local compute box)

REALITY CHECK (petrus, correctly): a Raspberry Pi 5 is NOT ~80 EUR on the
shelf in Europe. A usable KIT (board + PSU + case + storage) is **250-310
EUR** right now (the Aug 2026 Amazon.de listings we saw: db-tronic Pi 5 8GB
NVMe set 255, iRasptek Pi 5 16GB kit 326). The bare MSRP board is a number
you cannot actually buy at. So the Pi path's real base cost is ~**280 EUR**,
not 130.

**This flips the recommendation: the base station should probably NOT be a
Pi.** An x86 mini PC does the same job (Frigate + local vision), FASTER, for
LESS:

| Base option | Retail (1 off) | Notes |
|-------------|---------------:|-------|
| **Intel N100 mini PC (16GB/512GB)** | **~150-180** | runs the vision model several x faster than a Pi; x86, more RAM, SSD included; the value pick |
| Raspberry Pi 5 kit (8GB + PSU + case + SSD) | 255-310 | GPIO for display/mic, maker appeal, but pricier AND slower for vision |
| Reuse a box you own (old PC / NUC / the Bosgame) | 0 | if the buyer has one |

Base subtotal used below: **~165 EUR** (N100 mini PC as the default).

## Optional (phase-2, not in v1)

| Part | Retail | Volume est. |
|------|-------:|------------:|
| E-ink status display (Badger-class/HAT) | 25 | 15 |
| Mic + small speaker | 8 | 4 |
| USB backup stick/SSD | 10-40 | (user-supplied) |
| Printed display shroud + pendant cradle | 3 | 1.5 |

## Totals (corrected)

- **Core build with N100 mini PC base:** ~**71 + 165 = ~235 EUR** prototype.
- **Core build with Pi 5 kit base:** ~**71 + 280 = ~350 EUR** prototype
  (pricier and slower - only worth it for the GPIO/maker angle).
- **Reusing a box the buyer owns:** ~**71 EUR** (just the pendant).

The lesson: the pendant is cheap (~30-70), the COMPUTE is the whole cost
question, and a Pi is the expensive way to buy compute in 2026. Pricing
should assume a mini-PC-class base unless we deliberately choose the Pi for
its pins.

## Pricing tension (the honest part)

1. **The compute box is the cost floor and it is a general computer** -
   most of the BOM is a small always-on PC (mini PC ~165, or a Pi 5 kit
   ~280). Hardware margin on commodity compute is thin either way.
2. **The pitch is NO subscription**, so the hardware sale must carry all the
   margin. That is the opposite of the Ring/Nest model and it is a feature,
   but it means the sticker price has to include the value, not defer it.

### Three ways to price it

- **A. Full kit, assembled + flashed:** ~**299-349 EUR**. Everything in the
  box, plug in and go. Best story, healthiest margin, highest sticker.
- **B. Pendant kit, bring-your-own-Pi:** ~**99-129 EUR** for the pendant +
  SD image; "add any Raspberry Pi 5". Low entry price, appeals to the maker
  crowd, offloads the Pi cost to the buyer.
- **C. Two SKUs:** sell A to normal people and B to makers from the same
  design. Recommended - the software/image is identical, only the box
  differs.

### Reference points (different categories, for gut-check only)

- AirTag / Tile: ~30 EUR, but track ONE item via the phone network. Not a
  competitor - WhereWatch is passive whole-home memory, a different job.
- A Ring/Nest cam: ~60-100 EUR hardware **plus** a monthly cloud fee.
  WhereWatch trades the sticker up and the subscription to zero.

The differentiator that justifies price: **local, private, no monthly fee,
answers "where/did I" across the whole home** - nothing off-the-shelf does
that. Price on the value of never paying a subscription and never sending
your home to a cloud, not on the parts.
