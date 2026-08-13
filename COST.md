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

## Base station (the home Pi)

| Part | Retail (1 off) | Volume est. |
|------|---------------:|------------:|
| Raspberry Pi 5 (8GB) | 80 | 70 |
| 27W USB-C power supply | 12 | 8 |
| Storage: NVMe SSD 256GB (DB + photos) | 28 | 20 |
| Stock case | 10 | 6 |
| **Base subtotal** | **~130** | **~104** |

## Optional (phase-2, not in v1)

| Part | Retail | Volume est. |
|------|-------:|------------:|
| E-ink status display (Badger-class/HAT) | 25 | 15 |
| Mic + small speaker | 8 | 4 |
| USB backup stick/SSD | 10-40 | (user-supplied) |
| Printed display shroud + pendant cradle | 3 | 1.5 |

## Totals

- **Core two-device build, prototype prices:** ~**200 EUR** (71 + 130).
- **Core two-device build, volume BOM:** ~**130 EUR** (28 + 104).
- **With display + voice, prototype:** ~**235 EUR**.

## Pricing tension (the honest part)

1. **The Pi is the cost floor and it is a general computer** - ~half the BOM
   is a Raspberry Pi you cannot cost-reduce much. Hardware margin on a
   Pi-based product is thin.
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
