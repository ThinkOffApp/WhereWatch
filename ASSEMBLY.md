# WhereWatch pendant — the easy assembly guide

Plain words, one thing at a time. The technical checklist is
[BUILD.md](BUILD.md); this page is the version you follow at the table with
the parts box open. Every step ends with a check you can see.

Only **one** thing in this build needs a soldering iron: the battery lead
(step 8). Everything else plugs together with jumper wires. Do the whole
no-solder part first and get it working on USB power; solder the battery last.

## Before you start

On the table:

- the XIAO ESP32S3 Sense (thumb-sized board, USB-C, with the small camera
  board clipped on top)
- the OV5640 camera with its flat orange ribbon
- the GY-521 motion sensor (small blue board, 8 pins)
- the GPS module with the square ceramic antenna on a thin cable
- the 0.42 inch OLED (bare module, 4 pins: VCC GND SCL SDA)
- the slide switch, the button, the vibration module
- jumper wires (female-to-female "Dupont" leads are the easiest; if you only
  have bare silicone wire, that is where the iron comes in)
- a **mini breadboard** if you have one: the XIAO's pin headers plug straight
  into it and every pin gets several holes, which you need because two parts
  share the same two pins (step 3 and 4). Without a breadboard, twist two
  jumper ends into one for those pins.
- a USB-C cable and a computer or a power bank

Read the pin labels on the XIAO once: along the two long edges you see
**D0 D1 D2 D3 D4 D5** on one side and **5V GND 3V3 D10 D9 D8 D7 D6** on the
other. Those labels are what every step below refers to. Nothing is wired
to D8, D9 or D10, ever: the camera board uses them.

Rule for every step: **unplug the USB cable before you connect or move a
wire**, plug it back in for the check.

## 1. Does the brain live?

Plug the XIAO into the computer with USB-C. The board has no power light:
its only two LEDs are a charge LED (battery only, step 8) and a user LED
that stays dark until firmware drives it. So the sign of life is the
computer: it sees a new USB device (on a Mac: Apple menu > About This Mac >
System Report > USB, a "USB JTAG/serial debug unit" entry appears).

Check: device listed. If not, try another cable; many USB-C cables are
charge-only.

## 2. Camera

USB unplugged. The small board clipped on top of the XIAO already carries
a camera (the OV2640 Seeed ships) sitting in a flat connector with a dark
plastic bar along its edge. That bar is the latch.

1. Look at the old ribbon before touching it: note which way its shiny
   contact strip faces. The new one goes in the same way.
2. The whole black top of the connector lifts up like a small door. A
   fingernail is usually too soft: slide the tip of a small flat screwdriver
   or a plastic spudger under the black top at the ribbon edge and lever it
   upward; it swings up a few millimetres (build report on the same board:
   dronebotworkshop.com/xiao-esp32s3-sense). The old ribbon now slides out
   with no force.
3. Slide the OV5640's ribbon in straight, all the way forward, conductive
   side facing down toward the board.
4. Press the door back down until it stops.
5. Tug the ribbon very lightly: it must not move. Tape it flat with a
   strip of Kapton (the amber tape) so it cannot lever the latch open.

If the new ribbon is wider or narrower than the slot, stop: it is the wrong
module for this connector. The XIAO-fit OV5640 is the one that fits.

**If the door comes off** (it happens; it sits on two tiny side pivots):
if the bar is whole, set it back into the two slots at the ends of the
connector and press it down with the ribbon in place. If it is really
broken, the bench fix is: ribbon in, gold stripes down, all the way in, a
small pad of foam or folded paper on top of the ribbon end, and Kapton
pulled tight over the whole connector so the pad presses the ribbon onto
the contacts. Once the firmware shows a picture, a drop of hot glue over the
connector makes it permanent. The clean fix is a new XIAO ESP32S3 Sense (the
camera board comes with it); the damaged one stays the bench unit.

Check: the ribbon sits evenly, not skewed, and the latch is closed. There
is nothing to see on screen yet; the picture test comes with the firmware.

## 3. Motion sensor (GY-521)

Four wires. Label on the sensor → label on the XIAO:

| sensor pin | XIAO pin |
|-----------|----------|
| VCC | 3V3 |
| GND | GND |
| SCL | D5 |
| SDA | D4 |

Leave the sensor's other pins (XDA, XCL, AD0, INT) empty.

Solder or not? Look at the sensor. The "pin strip" is the row of pointed
metal pins in a black plastic strip (eight in a row on this sensor; the
XIAO has the same kind along both edges). If that row is already standing
up out of the sensor's board and does not come off, no solder, four female-to-female jumper wires from the sensor pins to
the XIAO header pins and you are done. If the row is a separate loose piece in
the bag, skip it and solder four wires straight into the sensor's four holes (VCC
GND SCL SDA) with jumper ends on the XIAO side: that is the final pendant
wiring anyway (no header, lies flat in the case), and four easy joints are
the right warm-up before the battery pads in step 8. No iron yet: push the
loose strip into the holes and tilt it so the pins touch; good enough for
a first reading, not for anything after.

Check: nothing visible yet. Keep the board flat; note which way "up" is.

## 4. The little screen (the purple board)

The purple board with the tiny screen is the pendant's face. It is a small
chip of its own that only shows what the XIAO tells it, and its spare pins
also work the vibration motor and the GPS switch. It needs its own little
program first (`firmware/face`; it gets flashed over the purple board's
USB-C, ask in the room and it is done from the MacBook in a minute).

Four wires, label on the purple board → label on the XIAO:

| purple pin | XIAO pin |
|-----------|----------|
| V3 | 3V3 |
| GD | GND |
| RX | D6 |
| TX | D7 |

RX to D6 and TX to D7: crossed, one talks, the other listens.

Check: with its program on it, the purple board shows "face ready" as soon
as it has power, even before the XIAO says anything. The Segor 1.3 inch
module stays in the drawer.

## 5. GPS

Four wires plus the antenna:

| GPS pin | XIAO pin |
|--------|----------|
| VCC | 3V3 |
| GND | GND |
| TX | D2 |
| RX | D3 |

TX goes to D2 and RX to D3: the module talks into the XIAO's ear and
listens to its mouth, so the labels cross. VCC on 3V3 is for the table
only: in the finished pendant the GPS gets its power through a small
switch that the purple board controls from its pin 3, so it can be off at
home (BUILD.md step 2c). Push the antenna's tiny round plug onto the
matching socket on the module until it clicks.

Check: if the module has an LED, it usually starts blinking only once it
has a satellite fix, which takes minutes and needs sky. Indoors, no blink
is normal.

## 6. Button and switch

Button: one leg to **D1**, the other leg to **GND**. Any two legs that are
not connected to each other (on a 4-leg button, take two legs that are
diagonally opposite).

Slide switch: it will sit in the battery lead later (step 8) so that the
pendant can be switched fully off. Leave it aside for now.

Check: nothing visible yet.

## 7. Vibration module

Three wires, and this one goes to the purple board, not the XIAO:
**VCC → XIAO 3V3**, **GND → XIAO GND**, **IN → purple board pin 10**.

Check: nothing until firmware. Hold the module in your hand later for the
first buzz, it is easy to miss on the table.

## 8. The battery (the one soldering step)

Do this last, with everything else already working on USB.

1. USB unplugged. Turn the XIAO over: two small pads on the underside,
   marked **B+** and **B−**.
2. Take the JST pigtail that mates with the battery's own plug (plug them
   together first to find the right one).
3. Put the slide switch into the **red** wire: cut the red wire, one half to
   the middle pin of the switch, the other half to one of the outer pins.
4. Red to **B+**, black to **B−**. Check the colours twice before the iron
   touches the board. Small blob of solder on each pad, wire on, heat,
   done. Shiny joint, no bridge between the pads.
5. Slip heat-shrink over each joint. Tape the wire down so a pull on the
   lead takes the tape, not the pad.
6. Plug the battery in. Switch on. Nothing lights by itself (no power LED
   on this board), so the check is the multimeter: black probe on GND,
   red on the **3V3** pin, it reads about 3.3 V with the switch on and 0 with
   it off. Then plug USB in: the charge LED comes on and goes off again when
   the cell is full.

Check: 3.3 V on the 3V3 pin from the battery alone; charge LED on USB.

## 9. What happens next

With the wiring done the pendant is a body without a mind: the firmware is
the next piece of work in this repo. Its first version shows on the little
screen which parts it can see (camera, motion, GPS, battery) so the check
for every step above becomes a line on the screen. Until then, the checks
are the visual ones written at each step.

Then the case: print `cad/pendant.stl`, clip the pin headers off the XIAO
(they are too tall for the case), place everything, close it.
