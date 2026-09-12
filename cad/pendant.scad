// WhereWatch pendant - TEARDROP, personalised
// petrus, Aug 16: "ylaosasta kapea ja pyorea, alhaalta leveampi
// pyoristetyilla kulmilla" - narrow round tip up, widening toward the
// battery. Form follows the parts: the tip only has to clear the GPS
// patch (13 mm), the bottom must clear the cell (40 mm).
// Worn vertically. Top end is a full half-dome (river stone), camera at the
// top, BATTERY IN THE BOTTOM half, and the back carries a PERSONAL engraving
// (your own text and/or emoji) so no two pendants look corporate.
//
// SIZE follows the battery. Real cell sizes (model code = T x W x L in mm):
//   603048  6.0 x 30 x 48  = 1000 mAh  -> fits a slim 80 x 35 x 10 pebble
//   654060  6.5 x 40 x 60  = 2100 mAh  -> needs ~88 x 45 x 11  (STILL THIN)
//   804050  8.0 x 40 x 50  = 2100 mAh  -> shorter but 13 mm thick
//   103450 10.0 x 34 x 50  = 2100 mAh  -> narrow but 14 mm thick
// Default below = the 2 Ah cell that stays thinnest (654060).
//
// Render preview:
//   openscad -o preview.png -D shape_only=true --imgsize=1100,820 \
//     --camera=0,0,0,58,0,30,190 pendant.scad
// Export STL: openscad -o pendant.stl pendant.scad

/* [Battery choice] */
bat_t = 6.5;    // cell thickness (654060 = 2100 mAh)
bat_w = 40;     // cell width
bat_l = 60;     // cell length

/* [Shell] */
// petrus, Aug 16: "paksuus hyvin lähellä akun paksuutta" - faces thinned to
// 1.2 mm so the pendant carries only ~2.4 mm of structure over the cell
// (654060 -> 9.4 mm total; 603048 preset -> 8.9 mm).
wall = 1.2;
fit  = 0.4;     // clearance around the cell

/* [Outer size - derived from the cell, so the shape always fits] */
wid   = bat_w + fit + 2*wall;          // bottom width ~43 (cell decides)
tip_d = 22;                            // narrow round tip (GPS needs ~16)
thick = bat_t + fit + 2*wall;          // ~9.4 at the battery half
// Option A (petrus, 2026-09-12): the sensor head is thicker so the carrier PCB (0.8 mm) fits under the GPS
// module and the XIAO with the JST connectors beneath: 1.2 + 6.2 (GPS) + 0.8 + 3.6 + 1.2 = 13.0. The hull
// tapers the thickness smoothly from the tip to the battery half.
head_thick = 13.0;
// Teardrop sensor zone is IN LINE down the taper: GPS patch alone in
// the narrow tip, then OV5640 + XIAO + IMU (camera and IMU stack in
// the thickness axis on the XIAO), then the cell in the wide bottom.
// len: the cell is 40 mm wide inside a 43 mm shell, so its corners only clear the rounded bottom
// above x = -46.2; +46 (not +42) is what leaves the sensor head its full 37.4 mm (claudeMB 2026-09-12).
len   = bat_l + 46;                    // 106

/* [Roundness] */
r_bot = 8;      // soft bottom corners (12 pushed the cell's corners through the shell)

/* [Openings] */
cam_d        = 9;      // camera lens (front, near the top)
cam_from_top = 30;   // camera sits on the XIAO Sense at board x = 20.5 (carrier layout, 2026-09-12)
usbc_w       = 9.5;    // USB-C in the bottom end
usbc_h       = 3.4;
btn_d        = 4;      // side button
btn_from_top = 25.5;   // SW2 on the carrier at x = 25.5, through the +y wall
sw_from_top  = 17.5;   // SW1 slide switch on the carrier at x = 33.5, slot through the -y wall
sw_l = 6; sw_w = 2.2;
usb_from_top = 30.5;   // XIAO USB-C at the +y side wall (board x = 20.5), no longer in the bottom end
// OLED WINDOW: OFF by default since 13 Sep 2026, and this is a decision, not an oversight.
// The window (x 40.5..52.5, y +-3.25, back of the tip) sits directly over FOUR parts on the
// board's back side: J3 the u.FL antenna connector is entirely inside it, R1 likewise, and U2
// the IMU and Q2 clip its edges. A search over the whole back face found NO clear rectangle for
// a window of any size down to 6 x 3.5 mm, so the panel cannot simply be moved. Cutting the
// window anyway would open a hole onto the antenna connector.
// J6, the panel's connector, stays on the board and is routed, so a future revision can add the
// display back without a board change. Set this true only after the tip's back side is re-laid.
oled_window = false;
oled_from_top = 6.5;   // 0.42" OLED window on the BACK of the tip, centred on y=0, x 40.5..52.5.
                       // The PANEL sits here; its connector J6 is elsewhere on the board at
                       // (37.20, 5.40) and reaches it by the flex tail. Do not conflate the two:
                       // an earlier note here said "header at board x = 44.5", which was never
                       // the connector position after the layout moved it.
oled_l = 12; oled_w = 6.5;
lan_d        = 3.5;    // lanyard cord hole through the top tip

/* [Personalisation - this is the anti-corporate bit] */
// Any text you like, engraved on the back. Leave "" for a blank back.
// Emoji: OpenSCAD's text() cannot render colour emoji, so at print time an
// emoji SVG is imported here instead - same recess, same depth.
engrave_text  = "petrus";
engrave_size  = 9;      // mm cap height
engrave_depth = 0.8;    // mm recess
engrave_font  = "DejaVu Sans:style=Bold";
// Optional emoji SVG engraved above the text (set to a file to enable):
engrave_svg   = "";     // e.g. "keys.svg"
emoji_size    = 12;

/* [Privacy marks - what the device promises the people around it] ------------------------------
 * A camera worn on a cord has to say what it does not do, on the side that faces other people,
 * which is the FRONT, beside the lens. Two marks, each a circle with a bar through it:
 *   no faces : a head and shoulders, crossed out
 *   no video : a camera body with its lens, crossed out
 * Engraved 0.6 mm into the front face at 9 mm across, big enough to read at arm's length.
 */
privacy_marks = true;
pm_d          = 9;      // mark diameter
pm_depth      = 0.6;
pm_stroke     = 0.9;    // ring and bar thickness

module ring_and_bar() {
    difference() { circle(d = pm_d); circle(d = pm_d - 2*pm_stroke); }
    rotate(-45) square([pm_d * 0.92, pm_stroke], center = true);
}
module no_faces_2d() {
    ring_and_bar();
    intersection() {                                   // head + shoulders, kept inside the ring
        circle(d = pm_d - 2.2*pm_stroke);
        union() {
            translate([0, pm_d*0.09]) circle(d = pm_d*0.30);                 // head
            translate([0, -pm_d*0.20]) scale([1, 0.62]) circle(d = pm_d*0.58); // shoulders
        }
    }
}
module no_video_2d() {
    ring_and_bar();
    intersection() {
        circle(d = pm_d - 2.2*pm_stroke);
        union() {
            translate([-pm_d*0.06, 0]) square([pm_d*0.40, pm_d*0.27], center = true);   // body
            translate([ pm_d*0.20, 0]) rotate(-90) polygon([[-pm_d*0.13, 0], [pm_d*0.13, 0], [0, pm_d*0.20]]); // lens
        }
    }
}
// cam_x is defined further down (line ~163), and OpenSCAD evaluates top-level assignments in
// order, so referring to it here silently yielded undef and a "Ignoring unknown variable"
// warning: the marks were NOT placed below the lens. Compute it from the same source instead.
pm_x    = (len/2 - cam_from_top) - 12;   // the pair sits below the lens, on the front
pm_cut  = 0.45;            // the dome is planed this deep so both marks cut evenly
pm_pad_l = pm_d + 3;
pm_pad_w = 2*pm_d + 6;
module privacy_pad() {
    // plane a shallow flat on the domed front, the same trick the back engraving uses
    translate([pm_x, 0, head_thick/2 - pm_cut])
        linear_extrude(height = thick)
            offset(r = 3) square([pm_pad_l - 6, pm_pad_w - 6], center = true);
}
module privacy_engraving() {
    pm_z = head_thick/2 - pm_cut;
    privacy_pad();
    for (i = [-1, 1])
        translate([pm_x, i * (pm_d/2 + 1.5), pm_z - pm_depth])
            linear_extrude(height = pm_depth + 0.2)
                if (i < 0) no_faces_2d(); else no_video_2d();
}

$fn = 48;

// ---- friendly pebble: big top dome hulled with two soft bottom corners ----
module pebble_solid(inset = 0) {
    hw = wid/2 - inset;
    tt = thick - 2*inset;
    hull() {
        // narrow round tip (top)
        translate([len/2 - tip_d/2, 0, 0])
            scale([1, 1, (head_thick - 2*inset) / tip_d]) sphere(d = tip_d - 2*inset);
        // wide bottom, rounded corners
        for (y = [-1, 1])
            translate([-len/2 + r_bot + inset, y * (hw - r_bot + inset/2), 0])
                scale([1, 1, tt / (2 * r_bot)]) sphere(r = r_bot - inset/2);
    }
}

cam_x = len/2 - cam_from_top;
btn_x = len/2 - btn_from_top;

// personal engraving on the BACK face (-z).
// The back is domed, so a flat cut would bite unevenly. We first plane a
// shallow FLAT PAD (like a signet flat on a pebble), then engrave into it -
// giving a constant-depth, always-legible mark.
pad_x   = -len/2 + 30;   // pad centre along the long axis
pad_l   = 46;            // pad length
pad_w   = 22;            // pad width
pad_cut = 0.5;           // how far the flat is planed into the dome
pad_z   = -thick/2 + pad_cut;   // resulting flat face height

module engrave_pad() {
    // remove everything below pad_z inside the pad footprint -> a flat oval
    translate([pad_x, 0, -thick]) linear_extrude(height = thick - thick/2 + pad_cut)
        offset(r = 5) square([pad_l - 10, pad_w - 10], center = true);
}

module engraving() {
    if (engrave_text != "")
        translate([pad_x - 7, 0, pad_z - engrave_depth])
            mirror([0, 1, 0]) linear_extrude(height = engrave_depth * 2)
                text(engrave_text, size = engrave_size, font = engrave_font,
                     halign = "center", valign = "center");
    if (engrave_svg != "")
        translate([pad_x + 13, 0, pad_z - engrave_depth])
            mirror([0, 1, 0]) linear_extrude(height = engrave_depth * 2)
                resize([emoji_size, emoji_size]) import(engrave_svg, center = true);
}

module personalise() { engrave_pad(); engraving(); }

module openings() {
    if (privacy_marks) privacy_engraving();
    // camera lens (front, +z)
    translate([cam_x, 0, 0]) cylinder(d = cam_d, h = thick + 2, center = true);
    // lanyard cord hole through the top tip
    translate([len/2 - 6, 0, 0]) cylinder(d = lan_d, h = thick + 2, center = true);
    // USB-C through the +y side wall at the XIAO (option A)
    translate([len/2 - usb_from_top - usbc_w/2, wid/2 - wall - 2, -usbc_h/2]) cube([usbc_w, wall + 4, usbc_h]);
    // side button (+y wall)
    translate([btn_x, wid/2 - wall - 1, 0]) rotate([-90, 0, 0]) cylinder(d = btn_d, h = wall + 3);
    // slide switch slot (-y wall)
    translate([len/2 - sw_from_top - sw_l/2, -wid/2 - 2, -sw_w/2]) cube([sw_l, wall + 4, sw_w]);
    // OLED window on the back of the tip (see oled_window above: off until the back is re-laid)
    if (oled_window) translate([len/2 - oled_from_top - oled_l/2, -oled_w/2, -head_thick/2 - 1]) cube([oled_l, oled_w, wall + 2]);
}

module body() {
    difference() {
        difference() { pebble_solid(); pebble_solid(inset = wall); }
        openings();
        personalise();
    }
}

/* [Component blocks - the layout drawing (layout_view=true) shows these] */
// WARNING, READ BEFORE COPYING THESE NUMBERS. They are NOT the BOM part's size.
// The BOM part is U3 = ATGM336H-5N31 (LCSC C90770), which measures 9.8 x 10.2 mm on the board
// and has NO ceramic patch: its antenna input is fed from J3, the u.FL, via the L1 bias-T.
// The 15.7 x 13.1 x 6.2 below is the older patch-carrying variant this shell was drawn around,
// and the whole tip still follows from it (tip_d = 22 "because GPS needs ~16", and 6.2 of the
// 13.0 mm head). The volume is DELIBERATELY KEPT, because it is now the reservation for the
// external active antenna the 5N31 requires and the enclosure otherwise has nowhere to put.
// OPEN, 13 Sep 2026: either swap U3 for a footprint-compatible patch variant, or fit an active
// patch on a pigtail into this cavity. Until that is decided the pendant CANNOT GET A FIX SEALED.
// @claudemm's 3D viewer copied these three numbers from this line, so the two artefacts agreeing
// was never corroboration. If you change them, change them here and re-derive, do not copy.
gps_l = 15.7; gps_w = 13.1; gps_t = 6.2;   // patch-variant envelope, kept as the antenna reservation
cam_l = 8.5;  cam_w = 8.5;  cam_t = 4.5;   // OV5640 head (FPC folds below)
mcu_l = 21;   mcu_w = 17.8; mcu_t = 3.6;   // XIAO ESP32S3 Sense
imu_l = 20;   imu_w = 16;   imu_t = 2.5;   // MPU-6050 breakout
haptic_d = 10; haptic_t = 2.7;             // coin vibration motor

module component_blocks() {
    // battery fills the bottom half
    color([1.0, 0.55, 0.1, 0.95])
        translate([-len/2 + r_bot - 1.16 + bat_l/2, 0, 0])   // as low as the rounded corner allows
            cube([bat_l, bat_w, bat_t], center = true);
    // carrier PCB (0.8 mm) in the head, x = +11 .. tip; GPS on its top face in the tip (board x = 38.5)
    color([0.1, 0.5, 0.2, 0.95])
        translate([len/2 - 20.4, 0, 0.4]) cube([38.8, 24, 0.8], center = true);
    color([0.2, 0.8, 0.4, 0.95])
        translate([38.5 - 51 + len/2 - 0, 0, 0.8 + gps_t/2])
            cube([gps_w, gps_l, gps_t], center = true);
    // camera just below the GPS, lens to the front face
    color([0.3, 0.6, 1.0, 0.95])
        translate([cam_x, 0, thick/2 - wall - cam_t/2])
            cube([cam_l, cam_w, cam_t], center = true);
    // XIAO under the camera zone, IMU stacked beneath it
    // XIAO on the top face at board x = 20.5, 21 mm across the board (USB-C at the +y wall); the LSM6DS3 IMU
    // is a 3 x 2.5 mm chip on the bottom face under the GPS zone (board x = 37)
    color([0.9, 0.2, 0.5, 0.95])
        translate([20.5, 0, 0.8 + mcu_t/2])
            cube([mcu_w, mcu_l, mcu_t], center = true);
    color([0.7, 0.4, 1.0, 0.95])
        translate([37, 0, -imu_t/2 - 0.5])
            cube([3, 2.5, 1], center = true);
    // haptic coin on the battery shoulder
    color([0.5, 0.5, 0.5, 0.95])
        translate([-len/2 + r_bot/2 + bat_l + 4, wid/2 - wall - haptic_d/2 - 1, 0])
            cylinder(d = haptic_d, h = haptic_t, center = true);
}

/* [Views] */
layout_view = false;   // true = transparent shell + internal component blocks
shape_only = false;
// ThinkOff fuchsia (never blue - blue is not a WhereWatch colour)
if (part != "both") { /* handled below */ } else if (layout_view) {
    component_blocks();
    color([0.85, 0.27, 0.94, 0.28]) body();
} else
color([0.85, 0.27, 0.94])
if (shape_only) {
    difference() {
        pebble_solid();
        translate([cam_x, 0, thick/2 - 1.2]) cylinder(d = cam_d, h = 3);
        translate([len/2 - 6, 0, 0]) cylinder(d = lan_d, h = thick + 2, center = true);
        personalise();
    }
} else body();


/* [Printing: the case has to open] ------------------------------------------------------------
 * The body above is a closed hollow pebble: correct as a shape, impossible to assemble. For
 * printing it is split into a FRONT half (camera and GPS side) and a BACK half (the engraved pad),
 * joined by a lip so they locate and stay shut. part="front" | "back" | "both" (both = preview).
 * Export:  openscad -o front.stl -D 'part="front"' pendant.scad
 */
part      = "both";
lip_h     = 2.0;    // how deep the lip reaches into the other half
lip_t     = wall/2; // lip wall, half the shell so it nests
seam_z    = 0;      // split plane, the pendant's mid-thickness
seam_gap  = 0.15;   // print clearance between the halves

module seam_lip() {
    // a band that follows the inner wall, standing up from the seam into the front half
    intersection() {
        difference() {
            pebble_solid(inset = wall);                 // inner surface
            pebble_solid(inset = wall + lip_t);         // minus a thinner shell = a band
        }
        translate([-len, -wid, seam_z]) cube([2*len, 2*wid, lip_h]);
    }
}
module seam_slot() {
    // the same band, grown by the print clearance, removed from the back half
    intersection() {
        difference() {
            pebble_solid(inset = wall - seam_gap);
            pebble_solid(inset = wall + lip_t + seam_gap);
        }
        translate([-len, -wid, seam_z - 0.01]) cube([2*len, 2*wid, lip_h + 0.02]);
    }
}
module half(front = true) {
    difference() {
        union() {
            intersection() {
                body();
                if (front) translate([-len, -wid, seam_z]) cube([2*len, 2*wid, thick]);
                else       translate([-len, -wid, seam_z - thick]) cube([2*len, 2*wid, thick]);
            }
            if (front) seam_lip();
        }
        if (!front) seam_slot();
    }
}
if (part == "front") color([0.85, 0.27, 0.94]) half(true);
else if (part == "back") color([0.75, 0.22, 0.84]) half(false);
