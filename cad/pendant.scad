// WhereWatch pendant enclosure - parametric ROUNDED PEBBLE
// Spec (petrus): ~80 x 35 x 10 mm, smooth pebble - no sharp corners against
// the chest. Fully rounded on every axis (soap-bar / worn-pebble form).
// Internal layout that makes 10mm work: battery and board SIDE BY SIDE along
// the length:  [ battery ~50x34x6.5 ][ XIAO + OV5640 ~21x18 ]
// Dimensions parametric; verify vs the real parts (duct-tape v0.1 = the
// measurement fixture) before printing rev A.
//
// Render:  openscad -o pendant.png pendant.scad
// Export:  openscad -o pendant.stl pendant.scad

/* [Pebble outer size] */
len   = 80;     // long axis (mm)
wid   = 35;     // width (mm)
thick = 10;     // thickness (mm) - slim, comfortable on the chest

/* [Shell] */
wall     = 1.8;    // wall thickness
gap      = 0.4;    // print clearance
seam_z   = 0;      // split plane at mid-height (0 = centre)

/* [Openings] */
cam_d     = 9;     // camera lens hole (OV5640)
cam_end   = 1;     // which end the camera sits: +1 = +x end
usbc_w    = 9.5;   // USB-C cutout width
usbc_h    = 3.4;   // USB-C cutout height
btn_d     = 4;     // side button hole
lanyard_d = 4;     // lanyard hole through the rounded end

$fn = 40;   // enough for a smooth pebble; keeps the hull+difference fast

// ---- a smooth pebble: hull of 8 corner spheres (radius = rounding) ----
module pebble(l, w, t, r) {
    hull() for (x = [-1, 1], y = [-1, 1], z = [-1, 1])
        translate([x*(l/2 - r), y*(w/2 - r), z*(t/2 - r)])
            sphere(r);
}

r_out = min(thick, wid) / 2;              // full doming top/bottom + soft ends
r_in  = max(r_out - wall, 0.6);

cam_x = cam_end * (len/2 - 16);           // camera near one end, over the board

module body() {
    difference() {
        // hollow pebble shell
        difference() {
            pebble(len, wid, thick, r_out);
            pebble(len - 2*wall, wid - 2*wall, thick - 2*wall, r_in);
        }
        // camera lens hole (through the top, +z)
        translate([cam_x, 0, thick/2 - 2]) cylinder(d = cam_d, h = wall + 4);
        // USB-C cutout on the -x end face
        translate([-len/2 - 1, -usbc_w/2, -usbc_h/2])
            cube([wall + 3, usbc_w, usbc_h]);
        // button hole on the +y side
        translate([cam_x - 12, wid/2 - 1, 0])
            rotate([-90, 0, 0]) cylinder(d = btn_d, h = wall + 3);
    }
    // lanyard loop: a small rounded ear off the -x end
    translate([-len/2 + 2, 0, 0])
        difference() {
            rotate([0, 90, 0]) cylinder(d = lanyard_d*2.6, h = 4, center = true);
            rotate([0, 90, 0]) cylinder(d = lanyard_d, h = 8, center = true);
        }
}

// shape_only = true renders just the solid outer pebble (fast, for a shape
// preview image). false renders the real hollow shell with all openings.
shape_only = false;

if (shape_only) {
    difference() {
        pebble(len, wid, thick, r_out);
        translate([cam_x, 0, thick/2 - 2]) cylinder(d = cam_d, h = 4);   // hint the lens
    }
} else {
    body();
}
