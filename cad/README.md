# WhereWatch CAD

Parametric enclosures (OpenSCAD, code-based CAD - every dimension a variable).

- `pendant.scad` - the wearable pendant case (body + snap lid, camera hole,
  USB-C cutout, button hole, lanyard loop). SKELETON: dimensions are first
  estimates and must be verified against the real assembled parts (the
  duct-tape v0.1 stack is the measurement fixture).
- (planned) `base-cradle.scad` - clip-on for the stock Pi/Argon case: display
  shroud + pendant dock cradle.

Render/edit: install OpenSCAD, open the file, F5 preview / F6 render, export
STL for any print service. No proprietary CAD, no build step, diffs in git.

Workflow: parts arrive -> measure -> set the variables -> print rev A ->
adjust where it pinches -> rev B.
