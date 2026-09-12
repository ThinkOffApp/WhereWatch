#!/usr/bin/env python3
"""WhereWatch carrier v0.3, option A layout (claudeMB, 2026-09-12): the board lives in the pendant's sensor head.

Run with KiCad's own python:  ~/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 gen_pcb.py
Reads out/carrier.net (kicad-cli sch export netlist --format kicadsexpr), writes wherewatch-carrier.kicad_pcb
and out/wherewatch-carrier.dsn for freerouting.

Geometry (pendant.scad on main, option A agreed 2026-09-12 14:20Z): pendant length 102, width 43, tip circle d 22
centred 11 mm from the tip; the cell (654060) sits in the bottom half and is shifted 3 mm toward the bottom so it ends at
x = +11.4; the head is thickened to 13.0 mm from x = +11 to the tip so JST PH connectors fit under the XIAO.
x runs along the pendant, +x toward the tip (tip end at x = 51); y across; z = 0 at the board's top face.
Top (F.Cu, faces the front/sky): XIAO sideways (USB-C at the +y side wall), GPS module in the tip.
Bottom (B.Cu, faces the back): everything else, incl. the OLED header (the display faces the back).
"""
import os, re, math, sys, functools
print = functools.partial(print, flush=True)
import pcbnew
from pcbnew import VECTOR2I_MM as MM

HERE = os.path.dirname(os.path.abspath(__file__))
STD = os.path.expanduser('~/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
LOCAL = {'WhereWatch': os.path.join(HERE, 'lib/WhereWatch.pretty'), 'Seeed_XIAO': os.path.join(HERE, 'lib/Seeed_XIAO.pretty')}
NET = os.path.join(HERE, 'out/carrier.net')
OUT = os.path.join(HERE, 'wherewatch-carrier.kicad_pcb')
DSN = os.path.join(HERE, 'out/wherewatch-carrier.dsn')

# ---- outline: inner cavity of the head, inset from the shell ----
INSET = 1.2 + 0.2          # wall + half the fit
X0 = 11.0                  # board starts where the cell ends (+0.4 fit)
TIP_CX, TIP_R = 40.0, 11.0 - INSET   # tip circle
def half_width(x):
    """outer shell half-width along the taper (hull line tip circle -> bottom corners), minus the inset"""
    if x >= TIP_CX:
        return math.sqrt(max(TIP_R**2 - (x - TIP_CX)**2, 0.0))
    return (21.5 - 0.1329 * (x + 39.0)) - INSET
def outline_points(step=0.5, inset=0.0):
    pts = []
    x = X0 + inset
    while x < TIP_CX: pts.append((x, -(half_width(x) - inset))); x += step
    for i in range(0, 181, 5):                       # tip arc, from -y round to +y
        a = math.radians(-90 + i); pts.append((TIP_CX + (TIP_R - inset) * math.cos(a), (TIP_R - inset) * math.sin(a)))
    x = TIP_CX - step
    while x >= X0 + inset: pts.append((x, half_width(x) - inset)); x -= step
    return pts

# ---- placement: ref -> (x, y, rotation_deg, side) ----
T, B = 'F', 'B'
PLACE = {
    # TOP face. Thickness budget for the 13.0 mm head: tip = 1.2 wall + 6.2 GPS + 0.8 board + ~1.2 low parts
    # + 1.2 wall = 10.6; middle = 1.2 + 3.6 XIAO + 0.8 + 6.0 JST + 1.2 = 12.8. GPS and the connectors are at
    # different x, which is what lets the head stay at 13.
    'U1': (20.5, 0.0, 0, T),       # XIAO ESP32S3 Sense, USB-C at the +y side wall
    'U3': (38.5, 0.0, 90, T),      # ATGM336H GPS module, patch to the sky, in the tip
    'L1': (46.2, 0.0, 0, T),       # bias-T on the RF pad's side
    # BOTTOM face, middle band: the three JST PH (surface-mount variant), wires exiting toward the cell
    'J1': (16.0, -5.8, 0, B),      # LiPo
    'J5': (16.0,  5.8, 0, B),      # speaker (optional build)
    'J4': (25.5, -5.8, 0, B),      # vibration motor
    'SW2': (25.5, 7.8, 0, B),      # button, actuated through the +y wall by a shell post
    # BOTTOM face, tip band: low parts only (3.6 mm of room under the board there)
    'SW1': (38.5, -6.0, 0, B),     # holes sit in the gap between the GPS module's two pad columns     # MSK-12C02 slide switch, actuator through the -y wall
    'U2': (37.0, 0.0, 0, B),       # LSM6DS3TR-C IMU
    'J3': (44.3, 0.0, 0, B),       # u.FL for the external GNSS antenna, under the module's tip
    'J6': (34.0, 5.4, 0, B),       # OLED tail connector (1 mm JST SH)
}
FP = {}   # ref -> lib:name, from the netlist
# layout-side footprint substitutions (claudeMB 2026-09-12): the through-hole JST PH drills land under the
# XIAO module's body, so the three battery/speaker/motor connectors use the surface-mount variant instead.
SUBST = {'Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal':
         'Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal',
         # the 2.54 mm OLED header does not fit the tip; a 1 mm JST SH does, and the 0.42" panel comes on a
         # flexible tail anyway. Schematic side: J6 becomes SM04B-SRSS-TB (claudemm).
         'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical':
         'Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal'}

# ---- netlist (kicad sexpr) ----
def sexpr(text):
    tok = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text)
    def parse(i):
        out = []
        while i < len(tok):
            t = tok[i]
            if t == '(':
                sub, i = parse(i + 1); out.append(sub)
            elif t == ')':
                return out, i + 1
            else:
                out.append(t[1:-1] if t.startswith('"') else t); i += 1
        return out, i
    return parse(0)[0][0]
def find(node, key): return [n for n in node[1:] if isinstance(n, list) and n and n[0] == key]
tree = sexpr(open(NET).read())
for comp in find(find(tree, 'components')[0], 'comp'):
    ref = find(comp, 'ref')[0][1]; fpname = find(comp, 'footprint')[0][1]; FP[ref] = SUBST.get(fpname, fpname)
nets = []
for net in find(find(tree, 'nets')[0], 'net'):
    name = find(net, 'name')[0][1]
    nodes = [(find(n, 'ref')[0][1], find(n, 'pin')[0][1]) for n in find(net, 'node')]
    nets.append((name, nodes))
print(f'netlist: {len(FP)} components, {len(nets)} nets')
AUTO = [r for r in FP if r not in PLACE]   # small parts placed by the packer below
print('packer places', AUTO)

# ---- board ----
board = pcbnew.BOARD(); print('stage: board')
ds = board.GetDesignSettings()
ds.SetCopperLayerCount(2)
# JLCPCB 2-layer economy rules: 0.127 mm trace/space, 0.3 mm drill -> use 0.15/0.15 and 0.5/0.3 vias
nc = ds.m_NetSettings.GetDefaultNetclass()           # KiCad 10 API
for setter, val in ((getattr(nc, 'SetTrackWidth', None), 0.15), (getattr(nc, 'SetClearance', None), 0.127),
                    (getattr(nc, 'SetViaDiameter', None), 0.5), (getattr(nc, 'SetViaDrill', None), 0.3)):
    if setter: setter(int(val * 1e6))
for setter, val in ((getattr(ds, 'SetCurrentTrackWidth', None), 0.15), (getattr(ds, 'SetCurrentViaSize', None), 0.5),
                    (getattr(ds, 'SetCurrentViaDrill', None), 0.3)):
    if setter: setter(int(val * 1e6))
ds.m_TrackMinWidth = int(0.127e6); ds.m_ViasMinSize = int(0.45e6); ds.m_MinThroughDrill = int(0.3e6); ds.m_MinClearance = int(0.127e6)
ds.m_CopperEdgeClearance = int(0.3e6)   # JLCPCB trace-to-edge minimum

print('stage: rules done')
# outline
pts = outline_points()
poly = pcbnew.PCB_SHAPE(board); poly.SetShape(pcbnew.SHAPE_T_POLY); poly.SetLayer(pcbnew.Edge_Cuts)
poly.SetPolyPoints([MM(x, y) for x, y in pts]); poly.SetFilled(False); poly.SetWidth(int(0.1e6))
board.Add(poly); print('stage: outline')

# nets
netinfo = {}
for name, _ in nets:
    n = pcbnew.NETINFO_ITEM(board, name); board.Add(n); netinfo[name] = n

print('stage: nets')
# footprints
fps = {}
for ref, libname in FP.items():
    lib, name = libname.split(':')
    path = LOCAL.get(lib, os.path.join(STD, lib + '.pretty'))
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None: sys.exit(f'footprint not found: {libname}')
    fp.SetReference(ref)
    x, y, rot, side = PLACE.get(ref, (60.0, 0.0, 0, B))   # AUTO parts park off-board until packed
    board.Add(fp); fps[ref] = fp                      # add BEFORE flipping: Flip on a board-less footprint segfaults (KiCad 10)
    fp.SetPosition(MM(x, y))
    if side == B: fp.Flip(MM(x, y), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    fp.SetOrientationDegrees(rot)
    # footprint origins are not their centres (the XIAO's is a corner): centre the pad+body bbox on the intended point
    c = fp.GetBoundingBox(False, False).GetCenter()
    fp.Move(pcbnew.VECTOR2I(int(x * 1e6) - c.x, int(y * 1e6) - c.y))
    bb = fp.GetBoundingBox(False, False)
    print(f'  {ref:4} {side} bbox x {bb.GetLeft()/1e6:6.1f}..{bb.GetRight()/1e6:6.1f}  y {bb.GetTop()/1e6:6.1f}..{bb.GetBottom()/1e6:6.1f}')
for fp in fps.values():                              # mechanical PTH pads with no annular ring -> NPTH
    for pad in fp.Pads():
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and pad.GetNumber() in ('', '0'):
            pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH); pad.SetLayerSet(pad.UnplatedHoleMask())
for name, nodes in nets:
    for ref, pin in nodes:
        fp = fps[ref]; hit = False
        for pad in fp.Pads():
            if pad.GetNumber() == pin: pad.SetNet(netinfo[name]); hit = True
        if not hit: print(f'  warning: {ref} pad {pin} not in footprint {FP[ref]}')

# ---- packer for the small parts: near the big parts they connect to, inside the outline, no overlaps ----
POWER = {'GND', '+3V3', 'VBAT', 'VBUS', 'BAT_RAW', '+5V', 'BAT+', 'BAT-'}
def bb_of(fp):
    b = fp.GetBoundingBox(False, False); return (b.GetLeft()/1e6, b.GetTop()/1e6, b.GetRight()/1e6, b.GetBottom()/1e6)
def inside(l, t, r, b, slack=0.3):
    for cx in (l, r):
        if cx < X0 + slack or cx > TIP_CX + TIP_R - slack: return False
        hw = half_width(cx) - slack
        if -t > hw or b > hw: return False
    return True
def overlaps(l, t, r, b, others, gap=0.35):
    return any(l < r2 + gap and l2 < r + gap and t < b2 + gap and t2 < b + gap for (l2, t2, r2, b2) in others)
placed = [bb_of(fps[r]) for r in PLACE if PLACE[r][3] == B]          # bottom-side obstacles
placed_top = [bb_of(fps[r]) for r in PLACE if PLACE[r][3] == T]      # top-side obstacles
for r in PLACE:                                                      # a through-hole part blocks both sides
    if any(pd.GetAttribute() != pcbnew.PAD_ATTRIB_SMD for pd in fps[r].Pads()):
        (placed_top if PLACE[r][3] == B else placed).append(bb_of(fps[r]))
anchor = {}
for name, nodes in nets:
    if name in POWER or name.startswith('unconnected'): continue
    bigs = [fps[r].GetPosition() for r, _ in nodes if r in PLACE]
    for r, _ in nodes:
        if r in AUTO and bigs: anchor.setdefault(r, []).extend(bigs)
order = sorted(AUTO, key=lambda r: -(bb_of(fps[r])[2] - bb_of(fps[r])[0]) * (bb_of(fps[r])[3] - bb_of(fps[r])[1]))
for ref in order:
    fp = fps[ref]; l, t, r, b = bb_of(fp); w, h = r - l, b - t
    pts_a = anchor.get(ref) or [MM(30, 0)]
    ax = sum(p.x for p in pts_a) / len(pts_a) / 1e6; ay = sum(p.y for p in pts_a) / len(pts_a) / 1e6
    best = None
    for side_try in (B, T):
        obst = placed if side_try == B else placed_top
        y = -13.0
        while y <= 13.0:
            x = X0 + 0.3
            while x <= TIP_CX + TIP_R:
                L, T_, R, B_ = x - w/2, y - h/2, x + w/2, y + h/2
                if inside(L, T_, R, B_, 0.25) and not overlaps(L, T_, R, B_, obst, 0.25):
                    d = (x - ax)**2 + (y - ay)**2
                    if best is None or d < best[0]: best = (d, x, y, side_try)
                x += 0.25
            y += 0.25
        if best is not None: break
    if best is None: print(f'  PACKER: no room for {ref}'); continue
    _, x, y, side_try = best
    if side_try == T and fp.IsFlipped(): fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    c = fp.GetBoundingBox(False, False).GetCenter()
    fp.Move(pcbnew.VECTOR2I(int(x * 1e6) - c.x, int(y * 1e6) - c.y))
    (placed if side_try == B else placed_top).append(bb_of(fp))
    print(f'  packed {ref:4} {"B" if side_try == B else "T"} at ({x:5.1f},{y:5.1f}) near ({ax:4.1f},{ay:4.1f})')
# geometry checks: courtyard/pad bbox inside the outline, no same-side overlaps (0.3 mm slack)
def bbox(fp):
    b = fp.GetBoundingBox(False, False); return (b.GetLeft()/1e6, b.GetTop()/1e6, b.GetRight()/1e6, b.GetBottom()/1e6)
problems = 0
for ref, fp in fps.items():
    l, t, r, b = bbox(fp)
    for cx in (l, r):
        hw = half_width(min(max(cx, X0), TIP_CX + TIP_R)) if cx <= TIP_CX + TIP_R else 0
        if cx < X0 - 0.3 or cx > TIP_CX + TIP_R + 0.3 or -t > hw + 0.6 or b > hw + 0.6:
            print(f'  OUTSIDE: {ref} bbox x {l:.1f}..{r:.1f} y {t:.1f}..{b:.1f} (half-width at x={cx:.1f}: {hw:.1f})'); problems += 1; break
refs = list(fps)
for a in range(len(refs)):
    for c in range(a + 1, len(refs)):
        fa, fb = fps[refs[a]], fps[refs[c]]
        if fa.GetLayer() != fb.GetLayer():
            # different sides: only a through-hole in one can clash with the other's pads
            def pth_box(f):
                ps = [pd for pd in f.Pads() if pd.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)]
                if not ps: return None
                xs = [pd.GetPosition().x/1e6 for pd in ps]; ys = [pd.GetPosition().y/1e6 for pd in ps]
                return (min(xs)-1, min(ys)-1, max(xs)+1, max(ys)+1)
            def pad_box(f):
                xs = [pd.GetPosition().x/1e6 for pd in f.Pads()]; ys = [pd.GetPosition().y/1e6 for pd in f.Pads()]
                return (min(xs)-0.3, min(ys)-0.3, max(xs)+0.3, max(ys)+0.3)
            def pth_pads(f): return [pd for pd in f.Pads() if pd.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)]
            drills = [(fa, pth_pads(fa), fb), (fb, pth_pads(fb), fa)]
            hit = False
            for _, ps, other in drills:
                for pd in ps:                                    # a drill must clear every pad on the other side
                    px, py = pd.GetPosition().x/1e6, pd.GetPosition().y/1e6
                    rad = max(pd.GetSize().x, pd.GetSize().y)/2e6 + 0.5
                    for op in other.Pads():
                        ox, oy = op.GetPosition().x/1e6, op.GetPosition().y/1e6
                        orad = max(op.GetSize().x, op.GetSize().y)/2e6
                        if abs(px-ox) < rad+orad and abs(py-oy) < rad+orad: hit = True; break
                    if hit: break
                if hit: break
            if hit: print(f'  DRILL CLASH: {refs[a]} and {refs[c]}'); problems += 1
            continue
        l1, t1, r1, b1 = bbox(fa); l2, t2, r2, b2 = bbox(fb)
        if l1 < r2 - 0.3 and l2 < r1 - 0.3 and t1 < b2 - 0.3 and t2 < b1 - 0.3:
            print(f'  OVERLAP: {refs[a]} and {refs[c]}'); problems += 1
print(f'geometry problems: {problems}')
print('stage: footprints+pads')
# ground pours both sides
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(netinfo['GND']); z.SetIsFilled(False)
    z.SetLocalClearance(int(0.15e6)); z.SetMinThickness(int(0.25e6))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)   # solid pad connections: thermal spokes starved on 0.15 mm rules
    ol = z.Outline(); ol.NewOutline()
    for x, y in outline_points(inset=0.45): ol.Append(int(x * 1e6), int(y * 1e6))
    board.Add(z)

print('stage: zones'); board.Save(OUT); print('wrote', OUT)
# the router routes up to the Edge.Cuts line, so hand it an outline inset by 0.35 mm, then put the real one back
inset_pts = outline_points(inset=0.35)
poly.SetPolyPoints([MM(x, y) for x, y in inset_pts])
ok = pcbnew.ExportSpecctraDSN(board, DSN); print('dsn', ok, DSN)
poly.SetPolyPoints([MM(x, y) for x, y in pts])
board.Save(OUT)
