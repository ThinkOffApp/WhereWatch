#!/usr/bin/env python3
"""Tie the ground pours together with stitching vias: the only unconnected items left are GND islands."""
import math, sys
import pcbnew
from pcbnew import VECTOR2I_MM as MM
sys.path.insert(0, '.')

VIA_D, VIA_DRILL, CLR = 0.6, 0.3, 0.30
board = pcbnew.LoadBoard('wherewatch-carrier.kicad_pcb')
gnd = board.FindNet('GND')

def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0: return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

def pad_gap(x, y, pd):
    """true distance to the pad rectangle: a half-long-side circle sits inside the corners and lies"""
    p, sz = pd.GetPosition(), pd.GetSize()
    ang = -pd.GetOrientation().AsRadians()
    dx, dy = x - p.x/1e6, y - p.y/1e6
    ca, sa = math.cos(ang), math.sin(ang)
    lx, ly = abs(dx*ca - dy*sa), abs(dx*sa + dy*ca)
    return math.hypot(max(lx - sz.x/2e6, 0.0), max(ly - sz.y/2e6, 0.0))

pads, vias, segs = [], [], []
for fp in board.GetFootprints():
    for pd in fp.Pads(): pads.append(pd)
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition(); vias.append((p.x/1e6, p.y/1e6, 0.3, t.GetNetname()))
    else:
        a, bb = t.GetStart(), t.GetEnd()
        segs.append((a.x/1e6, a.y/1e6, bb.x/1e6, bb.y/1e6, t.GetWidth()/2e6, t.GetNetname()))

# board outline from the generator, so the vias stay inside with edge clearance
import importlib.util
spec = importlib.util.spec_from_file_location('g', 'gen_pcb.py')
src = open('gen_pcb.py').read().split('# ---- placement:')[0].replace("HERE = os.path.dirname(os.path.abspath(__file__))", "HERE = '.'")
g = {'__name__': 'geom'}; exec(src, g)
half_width, X0, TIP_CX, TIP_R = g['half_width'], g['X0'], g['TIP_CX'], g['TIP_R']

def inside(x, y, m=1.3):   # 0.8 left four vias inside the board-edge clearance (grok)
    if x < X0 + m or x > TIP_CX + TIP_R - m: return False
    return abs(y) < half_width(x) - m

def clear(x, y):
    for pd in pads:
        if pad_gap(x, y, pd) < VIA_D/2 + (0.05 if pd.GetNetname() == 'GND' else CLR): return False
    for px, py, r, n in vias:
        if math.hypot(x - px, y - py) < r + VIA_D/2 + (0.05 if n == 'GND' else CLR): return False
    for x1, y1, x2, y2, w, n in segs:
        if seg_dist(x, y, x1, y1, x2, y2) < w + VIA_D/2 + (0.05 if n == 'GND' else CLR): return False
    return True

added = 0
y = -13.0
while y <= 13.0:
    x = X0
    while x <= TIP_CX + TIP_R:
        if inside(x, y) and clear(x, y):
            v = pcbnew.PCB_VIA(board); v.SetPosition(MM(x, y))
            v.SetWidth(int(VIA_D*1e6)); v.SetDrill(int(VIA_DRILL*1e6))
            v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetNet(gnd); board.Add(v)
            vias.append((x, y, 0.3, 'GND')); added += 1
        x += 1.4
    y += 1.4
print('stitching grid vias added:', added)

# Second pass: the 1.4 mm grid misses narrow pour fragments, and a fragment with no via in it is an
# unconnected GND area no matter how many vias sit elsewhere. Fill, then give every fragment its own via.
def refill(): pcbnew.ZONE_FILLER(board).Fill(board.Zones())
refill()
for rnd in range(6):
    need = []
    for z in board.Zones():
        sp = z.GetFilledPolysList(z.GetLayer())
        for i in range(sp.OutlineCount()):
            o = sp.Outline(i)
            if any(o.PointInside(pcbnew.VECTOR2I(int(vx*1e6), int(vy*1e6))) for vx, vy, _, _ in vias): continue
            need.append((z.GetLayer(), o))
    if not need: break
    fixed = 0
    for layer, o in need:
        bb = o.BBox(); best = None
        x = bb.GetLeft()/1e6
        while x <= bb.GetRight()/1e6:
            y = bb.GetTop()/1e6
            while y <= bb.GetBottom()/1e6:
                if o.PointInside(pcbnew.VECTOR2I(int(x*1e6), int(y*1e6))) and inside(x, y) and clear(x, y):
                    d = min(seg_dist(x, y, x1, y1, x2, y2) for x1, y1, x2, y2, _, _ in segs) if segs else 9
                    if best is None or d > best[0]: best = (d, x, y)
                y += 0.2
            x += 0.2
        if best is None: continue
        _, x, y = best
        v = pcbnew.PCB_VIA(board); v.SetPosition(MM(x, y))
        v.SetWidth(int(VIA_D*1e6)); v.SetDrill(int(VIA_DRILL*1e6))
        v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(gnd); board.Add(v); vias.append((x, y, 0.3, 'GND')); fixed += 1; added += 1
    print(f'  round {rnd}: {len(need)} fragments without a via, placed {fixed}')
    if not fixed: break
    refill()
print('stitching vias total:', added)
board.Save('wherewatch-carrier.kicad_pcb')
