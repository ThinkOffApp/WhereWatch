# WhereWatch — build checklist

Bench checklist for the first pendant prototype. Parts come from
[HARDWARE.md](HARDWARE.md) plus tonight's shopping list; the two-device design
lives in [ARCHITECTURE.md](ARCHITECTURE.md); the case is in [cad/](cad/).

Rules of the bench:

- **Protected LiPo only.** No unprotected cells anywhere near this bench.
- **Power off between steps.** Every solder joint is made with the battery
  *out* and the board on the mat, never live.
- Test after each step before adding the next one. A build that fails at
  step 5 should not require desoldering steps 1–4.

---

## 0. Lay out and verify (no solder yet)

- [ ] XIAO ESP32S3 Sense — board boots: USB-C to a computer, the onboard
      LED breathes, it enumerates as a serial device.
- [ ] LiPo **3.7V ~2000–2100mAh, protected, thin (~6.5mm)** — fits the
      pendant cavity in `cad/pendant.stl` dry-fitted without forcing.
- [ ] OV5640 camera module (5MP, wide 120–160°) — **fit check before
      ordering more of these**: it must mate with the XIAO Sense's camera
      connector (open question #1 in HARDWARE.md).
- [ ] IMU — MPU-6050 / GY-521 breakout.
- [ ] Button — 6mm momentary.
- [ ] Vibration motor — coin/LRA, plus N-channel transistor and flyback
      diode.
- [ ] JST battery pigtail (matches the LiPo's connector) + heat-shrink.
- [ ] Tools: USB-C soldering iron, lead-free solder, flux, tweezers,
      multimeter, Kapton tape.
- [ ] (Optional) GNSS module, e.g. ATGM336H, for the spare UART.

---

## Solder + bring-up order

Do these **strictly in order**. Camera ribbon goes on **last** — it is the
most fragile part of the build and should never be dangling over a hot iron
or test leads.

### 1. JST battery pigtail → XIAO battery pads ⚠️ the one real solder joint

The only solder joint this build truly needs. Do it first so the battery —
and with it, untethered testing of everything after — is available.

- [ ] Tin the two battery pads on the underside of the XIAO.
- [ ] Red → **B+**, black → **B−**. Double-check polarity against the silks
      before the iron touches anything. Use the half of the JST-PH pair that
      mates with the battery's own lead (plug them together first, then solder).
- [ ] Joint, inspect (shiny, wetted, no bridges), sleeve each pad with
      heat-shrink.
- [ ] Strain-relief the pigtail to the board edge so a yank takes the
      tape, not the pad.
- [ ] **First battery connect:** measure at the pads before attaching —
      ~3.7–4.2V, correct polarity. Then connect, and the onboard charge LED
      behaves when USB-C is plugged in.
- [ ] Battery voltage readable on an ADC pin (needed later for low-battery
      mode + honest haptic status). The XIAO ESP32S3 has no battery-sense
      pin and the cell is 3.7–4.2 V, so **never** wire B+ straight to a 3.3 V
      ADC input: two equal resistors (200 kΩ + 200 kΩ) from B+ to GND, the
      midpoint on the ADC pin, read ×2 in firmware. ~10 µA standing drain.

### 2. IMU on I2C

- [ ] GY-521 on the XIAO I2C pins (SDA/SCL), VCC 3V3, GND. Two signal
      wires, address 0x68 (or 0x69 with AD0 high).
- [ ] Bring-up: WHO_AM_I reads back 0x68/0x69; raw accel changes when the
      board tilts.
- [ ] Hot-glue / foam-tape the breakout flat inside the case footprint —
      it does half the leave-detection work and must not flex. Mark the
      axes on the tape so the firmware knows which way is down.

### 3. Button

- [ ] 6mm momentary across a GPIO + GND (internal pull-up), through the
      case button cut-out.
- [ ] Bring-up: debounced read of tap / double-tap / hold — these carry the
      voice-tag / status-buzz / power gestures from HARDWARE.md.

### 4. Vibration module

- [ ] Preferred: the **vibration motor module** on the shopping list (coin
      motor with a MOSFET driver on the board). Three wires: VCC → 3V3,
      GND → GND, IN → a GPIO. No discrete parts.
- [ ] Discrete alternative (no module): coin/LRA motor → NPN transistor
      (S8050 / 2N2222) → GPIO, **flyback diode across the motor terminals**
      (cathode to the + side), transistor base through **~1 kΩ** to the GPIO.
      (A 100 kΩ base resistor gives ~30 µA of base current: the transistor
      never saturates, the motor barely twitches and the transistor heats.)
- [ ] Bring-up: drive the agreed pattern — 1 buzz = on+connected,
      2 buzzes = offline, silence = off. Motor glued to a rigid case wall
      so you actually feel it through the pendant.

### 5. Camera ribbon — last

- [ ] Board powered **off**. Seat the OV5640 flex ribbon straight into the
      XIAO camera connector, latch it, tape the ribbon flat with Kapton.
- [ ] Bring-up: capture a frame; confirm focus and the wide-angle frame
      edges through the printed lens bezel.
- [ ] This is also the commissioning camera (QR scan in
      ARCHITECTURE.md) — check it decodes a phone-screen QR at arm's length
      before the board ever goes into the enclosure.

---

## 6. First full-system test (still no glue)

- [ ] On battery only: boots, streams to the base station (mini PC per
      ARCHITECTURE.md) over Wi-Fi.
- [ ] Haptic status patterns fire correctly off real connection state.
- [ ] IMU leave-detection and button gestures work untethered.
- [ ] Battery voltage → low-battery behaviour works; charges from the
      base station's USB-A dock cable.
- [ ] Run a day of wear-battery: this replaces every battery-life estimate
      in HARDWARE.md with the one measured number.

## 7. Enclosure

- [ ] **Clip or desolder the pre-soldered pin headers first.** The reordered
      XIAO is the pre-soldered variant; the pins add ~8 mm under the board and
      the teardrop is 9.3 mm thick. Headers are handy on the bench (Dupont
      jumpers for the IMU), fatal in the case. Do this after step 6 passes.
- [ ] Print the teardrop pendant from `cad/pendant.stl` (sources in
      `cad/pendant.scad`).
- [ ] Dry-fit everything; nothing pinches the camera ribbon or the battery.
- [ ] Lens, button, USB-C cut-outs align; lanyard loop clear of the cell.
- [ ] Only now: hot-glue final positions, close the case.

---

## Notes

- Pin map for the assembled pendant gets written into firmware config once
  the first board is alive; keep it next to this file when it exists.
- Open questions carried from HARDWARE.md: exact OV5640 module ↔ XIAO
  connector, ESP-SR wake-word RAM budget. Both block the *v2* parts order,
  not this build.
