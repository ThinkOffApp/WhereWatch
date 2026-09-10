#!/usr/bin/env python3
"""Centre-distance map for the animated ThinkOff heart (Petrus 2026-09-10 16:09Z: "colors cycling from
center to out, and also the background"). Each pixel gets its distance from the heart's core:
0 = core (2 px), 1, 2, 3 = rings outwards, 4 = background. Animate with
  colour(px) = PALETTE[(DIST[px] + phase) % 5]   (phase decreasing = colours travel outwards)
PALETTE (logo rings, core first): 74D42C green, FFC400 yellow, FF00E5 magenta, FF8DE6 pale pink, plus a
background colour of your choice as the fifth entry (the logo sits on white; on LEDs a dim 1A0A2E works).
Writes heart-depth.h and heart-depth.json next to this file."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
MASK = ["01100110","11111111","11111111","11111111","01111110","00111100","00011000","00000000"]
mask = [[int(c) for c in r] for r in MASK]
CORE = [(2, 3), (2, 4)]
def inside(y, x): return 0 <= y < 8 and 0 <= x < 8 and mask[y][x] == 1
def depth_of(y, x):
    if not mask[y][x]: return -1
    d = 0
    while True:
        d += 1
        for dy in range(-d, d + 1):
            for dx in range(-d, d + 1):
                if abs(dy) + abs(dx) <= d and not inside(y + dy, x + dx): return d - 1
dist = []
for y in range(8):
    row = []
    for x in range(8):
        d = depth_of(y, x)
        if (y, x) in CORE: row.append(0)
        elif d < 0: row.append(4)
        else: row.append(3 - min(d, 2))   # depth 0 (outer ring) -> 3, 1 -> 2, 2 -> 1
    dist.append(row)
json.dump({"name": "thinkoff-heart-dist", "rows": dist, "palette_core_first": ["74D42C", "FFC400", "FF00E5", "FF8DE6", "1A0A2E"]}, open(os.path.join(HERE, "heart-depth.json"), "w"), indent=1)
with open(os.path.join(HERE, "heart-depth.h"), "w") as f:
    f.write("// ThinkOff heart centre-distance map, 8x8 row-major top-left first. 0 = core, 1..3 rings outwards, 4 = background.\n")
    f.write("// colour = HEART_PALETTE[(THINKOFF_HEART_DIST[i] + phase) % 5]; step phase down every ~120 ms for an outward wave.\n")
    f.write("static const uint8_t THINKOFF_HEART_DIST[64] = {\n")
    for r in dist: f.write("  " + ", ".join(str(v) for v in r) + ",\n")
    f.write("};\nstatic const uint32_t HEART_PALETTE[5] = { 0x74D42C, 0xFFC400, 0xFF00E5, 0xFF8DE6, 0x1A0A2E };  // core first, background last\n")
for r in dist: print(" ".join(str(v) for v in r))
