#!/usr/bin/env python3
"""Generate the WhereWatch carrier-board schematic (KiCad 10 .kicad_sch).

Why a generator: the schematic is small, every net is named, and a text
generator keeps the pin map in BUILD.md, the BOM and the drawing in one place
that a reviewer can diff. Connectivity is by global labels placed exactly on
pin ends; KiCad's ERC (`kicad-cli sch erc`) is the check that the labels
actually meet the pins.

Run:  python3 hardware/gen_schematic.py && kicad-cli sch erc hardware/wherewatch-carrier.kicad_sch
"""
import os, re, uuid, sys

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_SYMS = os.path.expanduser('~/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols')
LOCAL_SYMS = os.path.join(HERE, 'lib')
OUT = os.path.join(HERE, 'wherewatch-carrier.kicad_sch')

# --------------------------------------------------------------------------
# symbol library access
# --------------------------------------------------------------------------
def find_symbol_block(text, name):
    i = text.find(f'(symbol "{name}"')
    if i < 0:
        return None
    depth, j = 0, i
    while True:
        c = text[j]
        if c == '"':
            j = text.find('"', j + 1)
            while text[j - 1] == '\\':
                j = text.find('"', j + 1)
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
        j += 1

_libcache = {}
def lib_text(lib):
    if lib not in _libcache:
        for base in (LOCAL_SYMS, KICAD_SYMS):
            p = os.path.join(base, lib + '.kicad_sym')
            if os.path.exists(p):
                _libcache[lib] = open(p, encoding='utf-8', errors='ignore').read()
                break
        else:
            raise FileNotFoundError(lib)
    return _libcache[lib]

def symbol_def(lib, name):
    """Flattened symbol block named 'lib:name' for the schematic's lib_symbols."""
    blk = find_symbol_block(lib_text(lib), name)
    if blk is None:
        raise KeyError(f'{lib}:{name}')
    m = re.search(r'\(extends "([^"]*)"\)', blk)
    props = dict(re.findall(r'\(property "([^"]*)" "([^"]*)"', blk))
    if m:
        # Derived symbol: flatten onto the parent's geometry (KiCad's ERC then
        # reports "symbol doesn't match copy in library" for these two parts;
        # accepted, it is a cosmetic mismatch, the pins are the parent's).
        parent = m.group(1)
        pblk = find_symbol_block(lib_text(lib), parent)
        out = pblk.replace(f'(symbol "{parent}"', f'(symbol "{lib}:{name}"', 1)
        out = re.sub(r'\(symbol "' + re.escape(parent) + r'_(\d+)_(\d+)"', lambda mm: f'(symbol "{name}_{mm.group(1)}_{mm.group(2)}"', out)
        for k in ('Value', 'Footprint', 'Datasheet', 'Description'):
            if k in props:
                out = re.sub(r'\(property "' + k + r'" "[^"]*"', f'(property "{k}" "{props[k]}"', out, count=1)
        pprops = dict(re.findall(r'\(property "([^"]*)" "([^"]*)"', pblk))
        return out, symbol_pins(pblk), {**pprops, **props}
    out = blk.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)
    return out, symbol_pins(blk), props  # sub-unit names stay bare (KiCad expects "R_0_1", not "Device:R_0_1")

def symbol_pins(blk):
    pins = []
    for m in re.finditer(r'\(pin (\w+) \w+\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\).*?\(name "([^"]*)".*?\(number "([^"]*)"', blk, re.S):
        pins.append(dict(num=m.group(6), name=m.group(5), x=float(m.group(2)), y=float(m.group(3)), rot=float(m.group(4)), etype=m.group(1)))
    # a symbol can list the same pad twice in different units; keep first per number
    seen, uniq = set(), []
    for p in pins:
        if p['num'] in seen:
            continue
        seen.add(p['num']); uniq.append(p)
    return uniq

# --------------------------------------------------------------------------
# the design
# --------------------------------------------------------------------------
# Each part: ref, lib, symbol, value, footprint override, position, and the net
# for every pin number. A pin missing from `nets` is left open (no-connect only
# where listed under `nc`).
PARTS = []
def part(ref, lib, sym, value, fp=None, at=(0, 0), nets=None, nc=(), extra_props=None):
    PARTS.append(dict(ref=ref, lib=lib, sym=sym, value=value, fp=fp, at=at, nets=nets or {}, nc=set(nc), props=extra_props or {}))

# --- the brain: XIAO ESP32S3 (Sense board clips on top) --------------------
part('U1', 'Seeed_XIAO', 'XIAO-ESP32-S3-SMD', 'XIAO ESP32S3 Sense', fp='Seeed_XIAO:XIAO-ESP32-S3-SMD', at=(60, 70), nets={
    '1': 'VBAT_SENSE',   # D0 / GPIO1  battery divider midpoint (ADC)
    '2': 'BTN',          # D1 / GPIO2  button to GND
    '3': 'GNSS_EN',      # D2 / GPIO3  GNSS power enable
    '4': 'VIB_IN',       # D3 / GPIO4  vibration driver
    '5': 'SDA',          # D4 / GPIO5
    '6': 'SCL',          # D5 / GPIO6
    '7': 'GNSS_RX',      # D6 / GPIO43 XIAO TX -> GNSS RX
    '8': 'GNSS_TX',      # D7 / GPIO44 XIAO RX <- GNSS TX
    '9': 'I2S_BCLK',     # D8 / GPIO7  (decision 5: no microSD)
    '10': 'I2S_LRCLK',   # D9 / GPIO8
    '11': 'I2S_DIN',     # D10 / GPIO9
    '12': '+3V3',        # 3V3_OUT
    '13': 'GND',
    '14': '+5V',         # VBUS
    '18': 'GND',
    '23': 'VBAT',        # battery pad (B+)
    '24': 'GND',         # battery pad (B-)
}, nc=('15', '16', '17', '19', '20', '21', '22', '25'), extra_props={'LCSC': 'C9900154951'})

# --- motion: LSM6DS3TR-C on I2C, address 0x6A (SA0 low) ---------------------
part('U2', 'Sensor_Motion', 'LSM6DS3', 'LSM6DS3TR-C', fp='Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y', at=(150, 40), nets={
    '1': 'GND',      # SDO/SA0 -> address 0x6A
    '5': '+3V3',     # VDDIO
    '6': 'GND', '7': 'GND',
    '8': '+3V3',     # VDD
    '12': '+3V3',    # CS high = I2C mode
    '13': 'SCL', '14': 'SDA',
}, nc=('2', '3', '4', '9', '10', '11'), extra_props={'LCSC': 'C967633'})   # INT1 unused in v0: no free XIAO pin (see README)

# --- GNSS: ATGM336H-5N31 (18 pads, user manual §2.4). Power gating uses the
# module's own ON/OFF pin (5, active-low shutdown) from D2 instead of an external
# high-side switch: fewer parts, and VBAT stays on +3V3 (10 uA) so a wake is a
# hot start (<=1 s) instead of a 35 s cold start. Review note: shutdown current
# is not specified in the manual; measure on the bench, and if it is not in the
# tens of uA, fall back to the P-MOSFET switch (BOM v0 lines 4-5).
part('U3', 'WhereWatch', 'ATGM336H', 'ATGM336H-5N31', fp='WhereWatch:ATGM336H-5N31', at=(150, 110), nets={
    '1': 'GND', '10': 'GND', '12': 'GND',
    '2': 'GNSS_TX', '3': 'GNSS_RX',
    '5': 'GNSS_EN',      # ON/OFF: high = run, low = shutdown (D2)
    '6': '+3V3',         # VBAT backup: RTC + ephemeris for hot start
    '8': '+3V3',         # VCC 2.7-3.6 V, 100 mA peak
    '11': 'GNSS_RF',
}, nc=('4', '7', '9', '13', '14', '15', '16', '17', '18'), extra_props={'LCSC': 'C90770'})
part('C1', 'Device', 'C', '10u', fp='Capacitor_SMD:C_0603_1608Metric', at=(130, 150), nets={'1': '+3V3', '2': 'GND'})
part('J3', 'Connector', 'Conn_Coaxial', 'u.FL GNSS antenna', fp='Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical', at=(190, 110), nets={'1': 'GNSS_RF', '2': 'GND'})

# --- vibration motor: low side N-MOSFET + flyback diode ----------------------
part('Q3', 'Transistor_FET', '2N7002', '2N7002', at=(80, 200), nets={'1': 'VIB_IN_R', '2': 'GND', '3': 'VIB_N'}, extra_props={'LCSC': 'C8545'})
part('R3', 'Device', 'R', '1k', fp='Resistor_SMD:R_0402_1005Metric', at=(65, 200), nets={'1': 'VIB_IN', '2': 'VIB_IN_R'})
part('D1', 'Diode', '1N4148W', '1N4148W', at=(110, 195), nets={'1': '+3V3', '2': 'VIB_N'}, extra_props={'LCSC': 'C81598'})   # K to +3V3, A to motor low side
part('J4', 'Connector_Generic', 'Conn_01x02', 'vibration motor', fp='Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal', at=(130, 200), nets={'1': '+3V3', '2': 'VIB_N'})

# --- speaker: MAX98357A I2S class-D, 4 ohm speaker ---------------------------
part('U4', 'Audio', 'MAX98357A', 'MAX98357A', at=(150, 175), nets={
    '1': 'I2S_DIN', '14': 'I2S_LRCLK', '16': 'I2S_BCLK',
    '4': '+3V3',          # SD_MODE high = left channel (mono)
    '7': '+5V', '8': '+5V',
    '3': 'GND', '11': 'GND', '15': 'GND', '17': 'GND',
    '9': 'SPK_P', '10': 'SPK_N',
}, nc=('2', '5', '6', '12', '13'), extra_props={'LCSC': 'C910544'})   # GAIN_SLOT open = 9 dB
part('C2', 'Device', 'C', '10u', fp='Capacitor_SMD:C_0603_1608Metric', at=(175, 160), nets={'1': '+5V', '2': 'GND'})
part('C3', 'Device', 'C', '100n', fp='Capacitor_SMD:C_0402_1005Metric', at=(185, 160), nets={'1': '+5V', '2': 'GND'})
part('J5', 'Connector_Generic', 'Conn_01x02', 'speaker 4R', fp='Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal', at=(190, 178), nets={'1': 'SPK_P', '2': 'SPK_N'}, extra_props={'LCSC': 'C173752'})

# --- screen: 0.42" I2C OLED module on a 4-pin header --------------------------
part('J6', 'Connector_Generic', 'Conn_01x04', 'OLED 0.42in I2C', fp='Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical', at=(190, 40), nets={'1': '+3V3', '2': 'GND', '3': 'SCL', '4': 'SDA'})
part('R4', 'Device', 'R', '4.7k', fp='Resistor_SMD:R_0402_1005Metric', at=(120, 30), nets={'1': '+3V3', '2': 'SDA'})
part('R5', 'Device', 'R', '4.7k', fp='Resistor_SMD:R_0402_1005Metric', at=(130, 30), nets={'1': '+3V3', '2': 'SCL'})

# --- battery, switch, sense divider, button ----------------------------------
part('J1', 'Connector_Generic', 'Conn_01x02', 'LiPo JST PH', fp='Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal', at=(20, 120), nets={'1': 'BAT_RAW', '2': 'GND'}, extra_props={'LCSC': 'C173752'})
part('SW1', 'Switch', 'SW_SPDT', 'MSK-12C02', fp='WhereWatch:MSK-12C02', at=(20, 100), nets={'2': 'BAT_RAW', '1': 'VBAT'}, nc=('3',), extra_props={'LCSC': 'C431540'})
part('R6', 'Device', 'R', '100k', fp='Resistor_SMD:R_0402_1005Metric', at=(35, 145), nets={'1': 'VBAT', '2': 'VBAT_SENSE'})
part('R7', 'Device', 'R', '100k', fp='Resistor_SMD:R_0402_1005Metric', at=(35, 160), nets={'1': 'VBAT_SENSE', '2': 'GND'})
part('C4', 'Device', 'C', '100n', fp='Capacitor_SMD:C_0402_1005Metric', at=(48, 160), nets={'1': 'VBAT_SENSE', '2': 'GND'})
part('SW2', 'Switch', 'SW_Push', 'TS-1187A', fp='Button_Switch_SMD:SW_SPST_TL3342', at=(20, 190), nets={'1': 'BTN', '2': 'GND'}, extra_props={'LCSC': 'C318884'})

# --- decoupling on the carrier rails ----------------------------------------
part('C5', 'Device', 'C', '100n', fp='Capacitor_SMD:C_0402_1005Metric', at=(175, 55), nets={'1': '+3V3', '2': 'GND'})
part('C6', 'Device', 'C', '10u', fp='Capacitor_SMD:C_0603_1608Metric', at=(185, 55), nets={'1': '+3V3', '2': 'GND'})

# --- power symbols + flags so ERC knows who drives the rails ------------------
POWER = [  # (ref, lib, sym, net, at)
    ('#PWR01', 'power', 'GND', 'GND', (30, 230)),
    ('#PWR02', 'power', '+3V3', '+3V3', (60, 225)),
    ('#PWR03', 'power', '+5V', '+5V', (90, 225)),
    ('#FLG01', 'power', 'PWR_FLAG', '+3V3', (60, 230)),
    ('#FLG02', 'power', 'PWR_FLAG', '+5V', (90, 230)),
    ('#FLG03', 'power', 'PWR_FLAG', 'VBAT', (120, 230)),
    ('#FLG04', 'power', 'PWR_FLAG', 'GND', (30, 235)),
]

# --- a local symbol for the GNSS module (not in KiCad's libraries) -----------
ATGM_PINS = [  # (number, name, side) -- ATGM336H-5N user manual §2.4, 18 pads
    ('1', 'GND', 'L'), ('2', 'TXD', 'R'), ('3', 'RXD', 'R'), ('4', '1PPS', 'R'),
    ('5', 'ON_OFF', 'R'), ('6', 'VBAT', 'L'), ('7', 'NC', 'L'), ('8', 'VCC', 'L'),
    ('9', 'nRESET', 'R'), ('10', 'GND', 'L'), ('11', 'RF_IN', 'L'), ('12', 'GND', 'L'),
    ('13', 'NC', 'L'), ('14', 'VCC_RF', 'L'), ('15', 'RSVD1', 'R'), ('16', 'SDA', 'R'),
    ('17', 'SCL', 'R'), ('18', 'RSVD2', 'R'),
]
def local_lib_symbols():
    """Symbols we define ourselves, in KiCad's own s-expression form."""
    pins = []
    li = ri = 0
    for num, name, side in ATGM_PINS:
        if side == 'L':
            x, y, rot = -12.7, 7.62 - li * 2.54, 0; li += 1
        else:
            x, y, rot = 12.7, 7.62 - ri * 2.54, 180; ri += 1
        et = 'power_in' if name in ('VCC',) else 'power_in' if name == 'GND' else 'passive'
        pins.append(f'''      (pin {et} line (at {x} {y} {rot}) (length 2.54)
        (name "{name}" (effects (font (size 1.27 1.27))))
        (number "{num}" (effects (font (size 1.27 1.27)))))''')
    return f'''    (symbol "WhereWatch:ATGM336H" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 11.43 0) (effects (font (size 1.27 1.27))))
      (property "Value" "ATGM336H-5N31" (at 0 -11.43 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "WhereWatch:ATGM336H" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
      (property "Datasheet" "https://www.lcsc.com/datasheet/lcsc_datasheet_2501061039_ZHONGKEWEI-ATGM336H-5N31_C90770.pdf" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
      (symbol "ATGM336H_0_1"
        (rectangle (start -10.16 10.16) (end 10.16 -10.16) (stroke (width 0.254) (type default)) (fill (type background))))
      (symbol "ATGM336H_1_1"
{chr(10).join(pins)}
      ))'''

def local_symbol_pins(name):
    pins = []
    li = ri = 0
    for num, nm, side in ATGM_PINS:
        if side == 'L':
            x, y, rot = -12.7, 7.62 - li * 2.54, 0; li += 1
        else:
            x, y, rot = 12.7, 7.62 - ri * 2.54, 180; ri += 1
        pins.append(dict(num=num, name=nm, x=x, y=y, rot=rot, etype='passive'))
    return pins

# --------------------------------------------------------------------------
# emit
# --------------------------------------------------------------------------
def U():
    return str(uuid.uuid4())

def label_angle(pin_rot):
    # a pin's rotation is the direction it points INTO the body; the label sits at its end
    return {0: 180, 180: 0, 90: 270, 270: 90}[int(pin_rot) % 360]

def main():
    lib_symbols, instances, labels, noconns = {}, [], [], []
    for p in PARTS:
        if p['lib'] == 'WhereWatch':
            lib_symbols['WhereWatch:ATGM336H'] = local_lib_symbols()
            pins = local_symbol_pins(p['sym'])
            fp_default = None
        else:
            block, pins, props = symbol_def(p['lib'], p['sym'])
            lib_symbols[f"{p['lib']}:{p['sym']}"] = block
            fp_default = props.get('Footprint', '')
        fp = p['fp'] or fp_default or ''
        X, Y = (round(v / 1.27) * 1.27 for v in p['at'])
        pin_by = {q['num']: q for q in pins}
        pin_by_name = {q['name']: q for q in pins}
        for key, net in p['nets'].items():
            q = pin_by.get(key) or pin_by_name.get(key)
            if q is None:
                sys.exit(f"{p['ref']}: no pin {key}")
            lx, ly = X + q['x'], Y - q['y']
            labels.append(f'  (global_label "{net}" (shape passive) (at {lx:.2f} {ly:.2f} {label_angle(q["rot"])}) (fields_autoplaced yes)\n    (effects (font (size 1.27 1.27)) (justify {"right" if label_angle(q["rot"]) == 180 else "left"}))\n    (uuid "{U()}")\n    (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {lx:.2f} {ly:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes))))')
        for key in p['nc']:
            q = pin_by.get(key) or pin_by_name.get(key)
            if q is None:
                sys.exit(f"{p['ref']}: no nc pin {key}")
            noconns.append(f'  (no_connect (at {X + q["x"]:.2f} {Y - q["y"]:.2f}) (uuid "{U()}"))')
        libid = f"{p['lib']}:{p['sym']}"
        extra = ''.join(f'\n    (property "{k}" "{v}" (at {X:.2f} {Y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))' for k, v in p['props'].items())
        instances.append(f'''  (symbol (lib_id "{libid}") (at {X:.2f} {Y:.2f} 0) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
    (uuid "{U()}")
    (property "Reference" "{p['ref']}" (at {X:.2f} {Y - 12:.2f} 0) (effects (font (size 1.27 1.27))))
    (property "Value" "{p['value']}" (at {X:.2f} {Y + 12:.2f} 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "{fp}" (at {X:.2f} {Y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (property "Datasheet" "" (at {X:.2f} {Y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes))){extra}
    (instances (project "wherewatch-carrier" (path "/{ROOT_UUID}" (reference "{p['ref']}") (unit 1)))))''')
    for ref, lib, sym, net, at in POWER:
        X, Y = (round(v / 1.27) * 1.27 for v in at)
        block, pins, props = symbol_def(lib, sym)
        lib_symbols[f'{lib}:{sym}'] = block
        q = pins[0]
        lx, ly = X + q['x'], Y - q['y']
        labels.append(f'  (global_label "{net}" (shape passive) (at {lx:.2f} {ly:.2f} {label_angle(q["rot"])})\n    (effects (font (size 1.27 1.27)) (justify left))\n    (uuid "{U()}"))')
        instances.append(f'''  (symbol (lib_id "{lib}:{sym}") (at {X:.2f} {Y:.2f} 0) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
    (uuid "{U()}")
    (property "Reference" "{ref}" (at {X:.2f} {Y + 4:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (property "Value" "{net if sym != 'PWR_FLAG' else 'PWR_FLAG'}" (at {X:.2f} {Y - 4:.2f} 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "" (at {X:.2f} {Y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (property "Datasheet" "" (at {X:.2f} {Y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (instances (project "wherewatch-carrier" (path "/{ROOT_UUID}" (reference "{ref}") (unit 1)))))''')

    sch = f'''(kicad_sch (version 20250114) (generator "gen_schematic.py") (generator_version "10.0")
  (uuid "{ROOT_UUID}")
  (paper "A3")
  (title_block (title "WhereWatch carrier PCB v0") (date "2026-09-09") (rev "v0") (company "ThinkOff") (comment 1 "generated by hardware/gen_schematic.py; connectivity by global labels; see hardware/README.md"))
  (lib_symbols
{chr(10).join(lib_symbols.values())}
  )
{chr(10).join(instances)}
{chr(10).join(labels)}
{chr(10).join(noconns)}
  (sheet_instances (path "/" (page "1")))
)
'''
    open(OUT, 'w').write(sch)
    print(f'wrote {OUT}: {len(PARTS)} parts, {len(labels)} labels, {len(noconns)} no-connects, {len(lib_symbols)} lib symbols')

ROOT_UUID = '7b0b4b2e-2c0d-4f5e-9a6a-000000000001'
if __name__ == '__main__':
    main()
