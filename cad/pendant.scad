// WhereWatch pendant - FRIENDLY PEBBLE, personalised
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
wall = 1.8;
fit  = 0.6;     // clearance around the cell

/* [Outer size - derived from the cell, so the shape always fits] */
wid   = bat_w + fit + 2*wall;          // ~45
thick = bat_t + fit + 2*wall;          // ~11
len   = bat_l + 28;                    // battery + board/camera zone (~88)

/* [Roundness] */
r_bot = 12;     // soft bottom corners

/* [Openings] */
cam_d        = 9;      // camera lens (front, near the top)
cam_from_top = 20;
usbc_w       = 9.5;    // USB-C in the bottom end
usbc_h       = 3.4;
btn_d        = 4;      // side button
btn_from_top = 33;
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

$fn = 48;

// ---- friendly pebble: big top dome hulled with two soft bottom corners ----
module pebble_solid(inset = 0) {
    hw = wid/2 - inset;
    tt = thick - 2*inset;
    hull() {
        translate([len/2 - wid/2, 0, 0])
            scale([1, 1, tt / wid]) sphere(d = wid - 2*inset);
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
    // camera lens (front, +z)
    translate([cam_x, 0, 0]) cylinder(d = cam_d, h = thick + 2, center = true);
    // lanyard cord hole through the top tip
    translate([len/2 - 6, 0, 0]) cylinder(d = lan_d, h = thick + 2, center = true);
    // USB-C in the bottom end face
    translate([-len/2 - 1, -usbc_w/2, -usbc_h/2]) cube([wall + 4, usbc_w, usbc_h]);
    // side button
    translate([btn_x, wid/2 - wall - 1, 0]) rotate([-90, 0, 0]) cylinder(d = btn_d, h = wall + 3);
}

module body() {
    difference() {
        difference() { pebble_solid(); pebble_solid(inset = wall); }
        openings();
        personalise();
    }
}

shape_only = false;
// ThinkOff fuchsia (never blue - blue is not a WhereWatch colour)
color([0.85, 0.27, 0.94])
if (shape_only) {
    difference() {
        pebble_solid();
        translate([cam_x, 0, thick/2 - 1.2]) cylinder(d = cam_d, h = 3);
        translate([len/2 - 6, 0, 0]) cylinder(d = lan_d, h = thick + 2, center = true);
        personalise();
    }
} else body();
