# WhereWatch carrier PCB (v0 schematic, ERC clean; layout pending)

**Goal (petrus, 2026-09-09):** the pendant electronics on one board, assembled by JLCPCB, so no soldering is needed at home. Mic, speaker, 0.42" screen, 5 MP camera, GPS, motion, vibration, on an ESP32.

**Architecture:** a carrier board for the **Seeed XIAO ESP32S3 Sense**. JLCPCB places the XIAO module itself (their part C9900154951); the Sense expansion board with the OV5640 camera, the PDM microphone and the microSD slot clips on top as today. Everything else sits on the carrier as bare parts JLC also solders.

## Pin map (from BUILD.md, the source of truth)

| XIAO pin | GPIO | carrier use |
|---|---|---|
| D0 | GPIO1 | battery divider midpoint (ADC), 100 k + 100 k + 100 nF |
| D1 | GPIO2 | button to GND (internal pull-up) |
| D2 | GPIO3 | GNSS power enable (drives the load switch) |
| D3 | GPIO4 | vibration motor driver IN |
| D4 | GPIO5 | I2C SDA: IMU + OLED |
| D5 | GPIO6 | I2C SCL: IMU + OLED |
| D6 | GPIO43 | UART TX → GNSS RX |
| D7 | GPIO44 | UART RX ← GNSS TX |
| D8 D9 D10 | GPIO7 8 9 | **I2S BCLK / LRCLK / DIN to the speaker amp** (decision 5 below): the XIAO ESP32S3's bottom pads carry only JTAG (used by the Sense board's mic and camera), USB, EN and the battery, so these three header pins are the only free GPIOs, and using them means **no microSD card in the pendant** |
| 3V3, GND, 5V, B+, B− | — | rails; battery via the XIAO's B+/B− pads |

## BOM v0 (JLCPCB part numbers verified 2026-09-09)

| # | function | part | JLC # | class |
|---|---|---|---|---|
| 1 | brain | Seeed XIAO ESP32S3 | C9900154951 | extended |
| 2 | motion | LSM6DS3TR-C, LGA-14 | C967633 | extended |
| 3 | GNSS | ATGM336H-5N31 | C90770 | extended |
| 4 | (dropped in v0.1: the ATGM336H has its own ON/OFF pin, see decision 5) | | | |
| 5 | vibration driver | 2N7002 N-MOSFET | C8545 | basic |
| 6 | flyback diode | 1N4148W | C81598 | basic |
| 7 | speaker amp | MAX98357A, TQFN-16 | C910544 | extended |
| 8 | screen | 0.42" 72x40 I2C OLED module | — | hand-fitted 4-pin header |
| 9, 12 | battery + speaker connectors | JST PH 2-pin S2B-PH-K-S | C173752 | extended |
| 10 | power switch | MSK-12C02 | C431540 | extended |
| 11 | button | TS-1187A-B-A-B | C318884 | basic |
| 13 | passives | 0402/0603 R, C | basic | basic |
| 14 | GNSS antenna connector | Hirose U.FL-R-SMT-1 (or equivalent) | tbd at review | extended |

## Open decisions (petrus / claudeMB)
1. GNSS antenna: u.FL + the ceramic patch from the parts box, or an on-board chip antenna.
2. Speaker: size and placement (15 mm 4 Ω candidate).
3. OLED on the carrier or on the case lid with a 4-wire lead.
4. Outline: teardrop from `cad/pendant.scad`, 1.0 mm board.
5. **GNSS gating (decided in v0.1, review it):** the module's ON/OFF pin (active-low shutdown) is driven from D2 instead of an external high-side MOSFET switch, and VBAT stays on 3V3 (10 µA) so every wake is a hot start (≤1 s, not 35 s). The manual does not state the shutdown current; if the bench shows more than tens of µA, the AO3401A high-side switch comes back.
6. **Speaker vs microSD:** the I2S amp needs three GPIOs and the only free ones are D8–D10, which the Sense board's SD slot also uses. Proposal: no SD in the pendant (the base station stores everything), amp on D8–D10. Alternative: drop the speaker (the pendant vibrates and shows text; the base station speaks).

## Verification before any order
Bench-prove the same circuit with the modules on jumper wires (ASSEMBLY.md) → KiCad ERC and DRC clean → JLCPCB DFM check on upload → second-agent review of the schematic against this pin map → first order 5 boards.

Room record: BOM v0 document `15fa6c35-3bc8-4eea-80b3-0ca6ff8ca643`, ideas line 9.

## Files
- `gen_schematic.py` → `wherewatch-carrier.kicad_sch` (regenerate after any edit; do not hand-edit the .kicad_sch). Connectivity is by global labels on pin ends.
- `sym-lib-table`, `fp-lib-table`, `wherewatch-carrier.kicad_pro`: project libraries (KiCad's bundled ones via `${KICAD10_SYMBOL_DIR}` / `${KICAD10_FOOTPRINT_DIR}`, plus `lib/`).
- `lib/`: vendored XIAO symbol + footprint (Seeed, CC BY-SA 4.0), the ATGM336H symbol, and footprints for the ATGM336H-5N31 and MSK-12C02 converted from the LCSC/EasyEDA records (see `lib/README.md`).
- `out/`: exported PDF/SVG/netlist of the current schematic.

## ERC status (KiCad 10.0.6, `kicad-cli sch erc --severity-all`)
0 errors. Accepted warnings: (1) `2N7002` and `1N4148W` are derived library symbols flattened by the generator, so ERC reports "doesn't match copy in library"; (2) LSM6DS3 SA0 tied to GND (address 0x6A) trips "bidirectional pin to power output" because GND carries a PWR_FLAG; (3) MAX98357A exposed pad to GND trips "unspecified pin to power input". None is a wiring fault.

## ATGM336H-5N31 pin table used (user manual §2.4)
1 GND · 2 TXD · 3 RXD · 4 1PPS · 5 ON/OFF (low = shutdown) · 6 VBAT · 7 NC · 8 VCC · 9 nRESET · 10 GND · 11 RF_IN · 12 GND · 13 NC · 14 VCC_RF · 15 reserved · 16 SDA · 17 SCL · 18 reserved. VCC 2.7–3.6 V, <25 mA running, 100 mA peak; UART default 9600.

## Review checklist before any order
- [ ] pin map above == BUILD.md == `gen_schematic.py` nets (second agent)
- [ ] footprint pad numbers for ATGM336H-5N31 and MSK-12C02 checked against the datasheets (converted from LCSC records; MSK-12C02: is pad 2 the common?)
- [ ] I2C addresses: LSM6DS3TR-C 0x6A, OLED 0x3C (no clash)
- [ ] I2S pins D8–D10 accepted (no microSD), decision 6
- [ ] GNSS ON/OFF gating accepted or MOSFET switch restored, decision 5
- [ ] bench-proof on jumper wires done (ASSEMBLY.md)
