#!/usr/bin/env python3
"""Close the connections the autorouter left open: a via beside each pad, an L on a free inner layer.

Run with KiCad's python after importing a session. Idempotent-ish: run once per routed board.
"""
import math, sys
import pcbnew
from pcbnew import VECTOR2I_MM as MM

B = 'wherewatch-carrier.kicad_pcb'
VIA_D, VIA_DRILL, TRACK_W, CLR = 0.6, 0.3, 0.15, 0.35
LAYER = pcbnew.In2_Cu

board = pcbnew.LoadBoard(B)

def obstacles():
    """every pad, via and track as (x, y, radius) circles, roughly"""
    out = []
    for fp in board.GetFootprints():
        for pd in fp.Pads():
            p = pd.GetPosition(); s = pd.GetSize()
            out.append((p.x/1e6, p.y/1e6, max(s.x, s.y)/2e6, pd.GetNetname()))
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition(); out.append((p.x/1e6, p.y/1e6, t.GetWidth()/2e6, t.GetNetname()))
    return out

def free_spot(near, net, obs, rmin=1.1, rmax=3.0):
    """nearest point to `near` where a via fits clear of everything not on this net"""
    nx, ny = near
    best = None
    r = rmin
    while r <= rmax:
        for i in range(72):
            a = math.radians(i * 5)
            x, y = nx + r * math.cos(a), ny + r * math.sin(a)
            ok = True
            for ox, oy, orad, onet in obs:
                if onet == net: continue
                if math.hypot(x - ox, y - oy) < orad + VIA_D/2 + CLR: ok = False; break
            if ok and (best is None or r < best[0]): best = (r, x, y)
        if best: break
        r += 0.25
    return None if best is None else (best[1], best[2])

def add_via(x, y, net):
    v = pcbnew.PCB_VIA(board); v.SetPosition(MM(x, y))
    v.SetWidth(int(VIA_D*1e6)); v.SetDrill(int(VIA_DRILL*1e6))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net); board.Add(v); return v

def add_track(p1, p2, layer, net):
    t = pcbnew.PCB_TRACK(board); t.SetStart(MM(*p1)); t.SetEnd(MM(*p2))
    t.SetWidth(int(TRACK_W*1e6)); t.SetLayer(layer); t.SetNet(net); board.Add(t)

# the two open connections, from the DRC report
OPEN = [('VBAT', ('U1', '23'), ('R6', '1')), ('VIB_IN', ('U1', '4'), ('R3', '1'))]
obs = obstacles()
for netname, (ra, pa), (rb, pb) in OPEN:
    net = board.FindNet(netname)
    def pad_of(ref, num):
        fp = board.FindFootprintByReference(ref)
        for pd in fp.Pads():
            if pd.GetNumber() == num: return pd
    A, Bp = pad_of(ra, pa), pad_of(rb, pb)
    pas = (A.GetPosition().x/1e6, A.GetPosition().y/1e6)
    pbs = (Bp.GetPosition().x/1e6, Bp.GetPosition().y/1e6)
    va = free_spot(pas, netname, obs); vb = free_spot(pbs, netname, obs)
    if not va or not vb: print(f'  {netname}: no room for a via'); continue
    add_via(*va, net); add_via(*vb, net)
    obs.append((va[0], va[1], VIA_D/2, netname)); obs.append((vb[0], vb[1], VIA_D/2, netname))
    add_track(pas, va, A.GetLayer(), net)               # pad to its via, on the pad's own layer
    add_track(pbs, vb, Bp.GetLayer(), net)
    mid = (vb[0], va[1])                                 # L on the inner layer
    add_track(va, mid, LAYER, net); add_track(mid, vb, LAYER, net)
    print(f'  {netname}: via {va[0]:.2f},{va[1]:.2f} -> {vb[0]:.2f},{vb[1]:.2f} on In2')

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(B); print('saved')
