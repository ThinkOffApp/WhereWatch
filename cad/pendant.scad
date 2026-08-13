// WhereWatch pendant enclosure - parametric starter
// STATUS: design skeleton. Dimensions are first estimates and MUST be
// verified against the real parts (measure the assembled duct-tape v0.1
// stack, per the README). Every number is a variable so refining is trivial.
//
// Render: openscad pendant.scad  (F6 to render, export STL)
// Parts assumed: XIAO ESP32S3 Sense (21 x 17.8mm) + OV5640 on ribbon,
// 2100mAh LiPo (~50 x 34 x 6.5mm), momentary button, vibration motor.

/* [Battery] */
bat_l = 50;   // measure your cell
bat_w = 34;
bat_h = 6.5;

/* [Board] */
board_l = 21;
board_w = 18;
board_h = 6;     // board + components + camera connector stack

/* [Case] */
wall     = 2.0;  // wall thickness
gap      = 0.4;  // print clearance around parts
corner_r = 4;    // rounded corner radius
lid_lip  = 1.2;  // lip depth for the snap lid

/* [Openings] */
cam_d      = 9;      // camera lens hole diameter (OV5640 module)
usbc_w     = 9.5;    // USB-C cutout width
usbc_h     = 3.5;    // USB-C cutout height
btn_d      = 4;      // button hole
lanyard_d  = 4;      // lanyard loop hole

// ---- derived inner cavity: battery beside/under board ----
inner_l = max(bat_l, board_l) + 2*gap;
inner_w = bat_w + 2*gap;
inner_h = bat_h + board_h + 2*gap;   // stacked
out_l = inner_l + 2*wall;
out_w = inner_w + 2*wall;
out_h = inner_h + 2*wall;

module rrect(l, w, h, r) {
  hull() for (x=[r, l-r], y=[r, w-r])
    translate([x, y, 0]) cylinder(r=r, h=h, $fn=48);
}

module body() {
  difference() {
    rrect(out_l, out_w, out_h, corner_r);
    // cavity
    translate([wall, wall, wall])
      rrect(inner_l, inner_w, inner_h + 1, max(corner_r-wall, 1));
    // camera lens hole (front face, centered on board zone, near top)
    translate([out_l/2, out_w/2, -1])
      cylinder(d=cam_d, h=wall+2, $fn=48);
    // USB-C cutout (bottom edge - charge + data)
    translate([out_l/2 - usbc_w/2, -1, wall+2])
      cube([usbc_w, wall+2, usbc_h]);
    // button hole (side)
    translate([-1, out_w/2, out_h/2])
      rotate([0,90,0]) cylinder(d=btn_d, h=wall+2, $fn=32);
  }
  // lanyard loop
  translate([out_l/2, out_w - 1, out_h - lanyard_d])
    rotate([90,0,0]) difference() {
      cylinder(d=lanyard_d*2.4, h=3, $fn=40);
      translate([0,0,-1]) cylinder(d=lanyard_d, h=5, $fn=40);
    }
}

module lid() {
  translate([0, out_w + 8, 0]) {
    rrect(out_l, out_w, wall, corner_r);
    // snap lip
    translate([wall+gap, wall+gap, wall])
      rrect(inner_l - 2*gap, inner_w - 2*gap, lid_lip, max(corner_r-wall,1));
  }
}

body();
lid();

// NOTE: this is a skeleton to iterate on. Before printing rev A: confirm
// the stack height (battery + board + camera), the camera lens center vs the
// board's actual camera position, and that the USB-C cutout aligns with the
// XIAO's port. Print, adjust the variables where it pinches, print rev B.
