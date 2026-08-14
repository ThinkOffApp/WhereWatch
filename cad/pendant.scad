// WhereWatch pendant - FRIENDLY PEBBLE (worn vertically)
// Spec (petrus): ~80 x 35 x 10 mm, all rounded, TOP extra-domed (teardrop /
// river-stone), camera near the top, BATTERY IN THE BOTTOM half, embedded
// emoji badges on the back. No sharp corners anywhere.
//
// As worn: +x = UP. Top end is a full half-dome (radius = wid/2); bottom is
// softly rounded. Layout inside:
//     top:    XIAO ESP32S3 + OV5640 (camera looks out the front near the top)
//     bottom: LiPo battery
// Interior thickness at 10mm outer / 1.8 walls is ~6.4mm -> battery must be
// <= ~6mm thick and <= ~30-31mm wide (see BATTERY NOTE in the room/SHOPPING).
//
// Render solid shape preview (fast):
//   openscad -o preview.png -D shape_only=true --imgsize=1100,760 \
//     --camera=0,0,0,60,0,30,175 --colorscheme=Tomorrow pendant.scad
// Export STL: openscad -o pendant.stl pendant.scad

/* [Outer size] */
len   = 80;    // long axis, worn vertically (mm)
wid   = 35;    // width (mm)
thick = 10;    // thickness (mm)

/* [Shell] */
wall = 1.8;
gap  = 0.4;

/* [Roundness] */
r_bot = 10;    // bottom corner roundness (soft)
// top end: full half-dome of radius wid/2 (maximum friendly)

/* [Openings] */
cam_d      = 9;     // camera lens (front face, near the top)
cam_from_top = 22;  // lens centre distance below the very top tip
usbc_w     = 9.5;   // USB-C in the bottom end face
usbc_h     = 3.4;
btn_d      = 4;     // button on the right side, thumb height
btn_from_top = 34;
lan_d      = 3.5;   // lanyard cord hole through the top dome tip
emoji_d    = 8;     // three shallow emoji badge recesses on the back
emoji_depth= 0.8;   // deboss depth (glyphs come from SVG import at print rev)

$fn = 48;

zs = thick / wid;          // z-squash for the top dome ellipsoid
zb = thick / (2 * r_bot);  // z-squash for bottom corner ellipsoids

// ---- friendly pebble: hull of a big top half-dome + two soft bottom corners
module pebble_solid(l = len, w = wid, t = thick, inset = 0) {
    hw = w/2 - inset;           // half width
    tt = t - 2*inset;           // thickness
    hull() {
        // top: one full-width ellipsoid -> semicircular, extra-domed top
        translate([l/2 - w/2, 0, 0])
            scale([1, 1, tt / w]) sphere(d = w);
        // bottom: two soft corner ellipsoids
        for (y = [-1, 1])
            translate([-l/2 + r_bot + inset, y * (hw - r_bot + inset/2), 0])
                scale([1, 1, tt / (2 * r_bot)]) sphere(r = r_bot - inset/2);
    }
}

cam_x = len/2 - cam_from_top;
btn_x = len/2 - btn_from_top;

module body() {
    difference() {
        // hollow shell
        difference() {
            pebble_solid();
            pebble_solid(inset = wall);
        }
        // camera lens hole, front face (+z), near the top
        translate([cam_x, 0, 0]) cylinder(d = cam_d, h = thick, $fn = 48);
        // USB-C, bottom end face
        translate([-len/2 - 1, -usbc_w/2, -usbc_h/2])
            cube([wall + 4, usbc_w, usbc_h]);
        // button, right side (+y)
        translate([btn_x, wid/2 - wall - 1, 0])
            rotate([-90, 0, 0]) cylinder(d = btn_d, h = wall + 3);
        // lanyard cord hole straight through the top dome tip
        translate([len/2 - 5, 0, 0]) cylinder(d = lan_d, h = thick + 2, center = true);
        // three emoji badge recesses on the BACK (-z): privacy trio spots
        for (i = [-1, 0, 1])
            translate([i * 12 - 6, 0, -thick/2])
                cylinder(d = emoji_d, h = emoji_depth * 2, center = true);
    }
}

// BATTERY BAY (bottom half interior): fits a cell up to ~30 x 48 x 6 mm
// (e.g. 603048-class ~900-1000mAh). The 654060 cell (40 x 61) does NOT fit
// this 35mm-wide shape - see SHOPPING/room note.

shape_only = false;
if (shape_only) {
    difference() {
        pebble_solid();
        translate([cam_x, 0, thick/2 - 1.2]) cylinder(d = cam_d, h = 3);
        translate([len/2 - 5, 0, 0]) cylinder(d = lan_d, h = thick + 2, center = true);
        for (i = [-1, 0, 1])
            translate([i * 12 - 6, 0, -thick/2])
                cylinder(d = emoji_d, h = emoji_depth * 2, center = true);
    }
} else {
    body();
}
