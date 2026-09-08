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
- [ ] GNSS module (in hand: small shielded UART receiver + ceramic patch
      antenna on a u.FL pigtail) for the spare UART.
- [ ] 0.42" 72x40 I2C OLED, **bare 4-pin module** (VCC GND SCL SDA). The
      purple ESP32-C3 board with the same panel on it is a second
      microcontroller, not a display: keep it for a desk beacon, do not
      wire it into the pendant.
- [ ] Mic: none to add — the Sense expansion board carries the PDM mic
      (reserved pins, see the pin map below).

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
      midpoint on **D0** (ADC), read ×2 in firmware. ~10 µA standing drain.

### 2. IMU on I2C

- [ ] GY-521 on the XIAO I2C pins (SDA/SCL), VCC 3V3, GND. Two signal
      wires, address 0x68 (or 0x69 with AD0 high).
- [ ] Bring-up: WHO_AM_I reads back 0x68/0x69; raw accel changes when the
      board tilts.
- [ ] Hot-glue / foam-tape the breakout flat inside the case footprint —
      it does half the leave-detection work and must not flex. Mark the
      axes on the tape so the firmware knows which way is down.

### 2b. OLED on the same I2C

- [ ] The 0.42" OLED shares the bus with the IMU: VCC → 3V3, GND → GND,
      SCL → D5, SDA → D4 (same two wires, second device). Its I2C address
      must differ from the IMU's 0x68/0x69; check the module's silk or
      listing [verify] (these panels usually sit at 0x3C).
- [ ] Bring-up: an I2C scan shows two devices; the panel draws a test line.
      Default face: dark. It lights on a button tap or a wrist-flick from
      the IMU and goes dark again after a few seconds — an OLED spends power
      only on lit pixels, so the face costs nothing while it is off.
- [ ] Mount it behind a window in the wide end of the case with a lip
      around the glass (it rides on a chest); add the window to
      `cad/pendant.scad` before the next print.

### 2c. GNSS on the spare UART

- [ ] Module GND → GND, module **TX → D7 (XIAO RX)**, module
      **RX → D6 (XIAO TX)**. Patch antenna on the u.FL pigtail, antenna
      face toward the lens side of the case (sky side when worn).
- [ ] Module VCC **not** straight to 3V3: the XIAO's 3V3 rail is always on,
      so firmware could never switch the receiver off. Bench: VCC → 3V3 is
      fine for bring-up. Final build: VCC through a small high-side load
      switch (P-MOSFET or a load-switch module) whose control pin is **D2**,
      or the module's own enable/standby pin if it has one [verify on the
      module]. Firmware then holds D2 off at home.
- [ ] Bring-up: NMEA sentences arrive on the UART at the module's default
      baud (printed on its listing/label [verify]); take it outdoors and
      wait for the first fix — a cold start can take minutes, that is normal.
- [ ] Power: the receiver is the pendant's steadiest drain after Wi-Fi, so
      firmware keeps it off at home (Wi-Fi visible) and powers it only when
      the leave-detector fires (HARDWARE.md: away-from-home location).

### 3. Button

- [ ] 6mm momentary across **D1** + GND (internal pull-up), through the
      case button cut-out.
- [ ] Bring-up: debounced read of tap / double-tap / hold — these carry the
      voice-tag / status-buzz / power gestures from HARDWARE.md.

### 4. Vibration module

- [ ] Preferred: the **vibration motor module** on the shopping list (coin
      motor with a MOSFET driver on the board). Three wires: VCC → 3V3,
      GND → GND, IN → **D3**. No discrete parts.
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

## Pin map (XIAO ESP32S3 Sense)

Labels as printed on the XIAO; GPIO numbers from Seeed's XIAO ESP32S3
getting-started page (pin map table). This is the map the firmware config
will carry; change it here first.

| XIAO pin | GPIO | Pendant use |
|----------|------|-------------|
| D0 | GPIO1 | battery divider midpoint (ADC), step 1 |
| D1 | GPIO2 | button to GND, internal pull-up, step 3 |
| D2 | GPIO3 | GNSS power enable (load switch or module EN), step 2c |
| D3 | GPIO4 | vibration module IN, step 4 |
| D4 | GPIO5 | I2C SDA: IMU + OLED, steps 2 and 2b |
| D5 | GPIO6 | I2C SCL: IMU + OLED, steps 2 and 2b |
| D6 | GPIO43 | UART TX → GNSS RX, step 2c |
| D7 | GPIO44 | UART RX ← GNSS TX, step 2c |
| D8 D9 D10 | GPIO7 GPIO8 GPIO9 | reserved by the Sense board (SD-card SPI), do not use |
| 3V3 | — | IMU, OLED, GNSS supply |
| B+ / B− | — | battery pads (underside), step 1 |

Not on the header but taken by the Sense board (Seeed pages): microphone on
GPIO41/42, SD-card CS on GPIO21, camera on GPIO10–18, 38–40, 47, 48.
Nothing else may be wired to those.

## Notes

- The pin map above is the one the firmware config carries; keep the two
  in step.
- Open questions carried from HARDWARE.md: exact OV5640 module ↔ XIAO
  connector, ESP-SR wake-word RAM budget. Both block the *v2* parts order,
  not this build.
