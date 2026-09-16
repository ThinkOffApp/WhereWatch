# WhereWatch carrier PCB (v0.3 schematic after two review passes, ERC clean; layout pending)

**Goal (petrus, 2026-09-09):** the pendant electronics on one board, assembled by JLCPCB, so no soldering is needed at home. Mic, speaker, 0.42" screen, 5 MP camera, GPS, motion, vibration, on an ESP32.

**Architecture:** a carrier board for the **Seeed XIAO ESP32S3 Sense**. JLCPCB places the XIAO module itself (their part C9900154951); the Sense expansion board with the OV5640 camera, the PDM microphone and the microSD slot clips on top as today. Everything else sits on the carrier as bare parts JLC also solders.

## Pin map (the carrier map; BUILD.md on main also carries the bench-build map with the purple face board, to be relabelled)

| XIAO pin | GPIO | carrier use |
|---|---|---|
| D0 | GPIO1 | battery divider midpoint (ADC), 100 k + 100 k + 100 nF |
| D1 | GPIO2 | button to GND (internal pull-up) |
| D2 | GPIO3 | GNSS ON/OFF (module pin 5, active-low shutdown), 100 k pulldown |
| D3 | GPIO4 | vibration motor driver IN |
| D4 | GPIO5 | I2C SDA: IMU + OLED |
| D5 | GPIO6 | I2C SCL: IMU + OLED |
| D6 | GPIO43 | UART TX → GNSS RX |
| D7 | GPIO44 | UART RX ← GNSS TX |
| D8 D9 D10 | GPIO7 8 9 | **I2S BCLK / LRCLK / DIN to the speaker amp** (decision 5 below): the XIAO ESP32S3's bottom pads carry only JTAG (used by the Sense board's mic and camera), USB, EN and the battery, so these three header pins are the only free GPIOs, and using them means **no microSD card in the pendant** |
| 3V3, GND, VBUS, B+, B− | — | rails; the cell reaches B+ through Q1; VBUS (USB present) only senses, via R2/R10 into Q2 |

## BOM v0 (JLCPCB part numbers verified 2026-09-09)

| # | function | part | JLC # | class |
|---|---|---|---|---|
| 1 | brain | Seeed XIAO ESP32S3 | C9900154951 | extended |
| 2 | motion | LSM6DS3TR-C, LGA-14 | C967633 | extended |
| 3 | GNSS | ATGM336H-5N31 | C90770 | extended |
| 4 | battery load switch | AO3401A P-MOSFET (Q1, 4 A) between the cell and the XIAO B+; gate 100 k up to the cell (off), pulled low by SW1 ("on") or by Q2 when USB is present | C15127 | basic |
| 5 | drivers (x2) | Q2 2N7002 (USB-present → Q1 on) C8545; Q3 AO3400A for the motor, RDS(on) specified at 2.5 V, 5.8 A | C8545 / C20917 | basic |
| 6 | flyback diode | 1N4148W | C81598 | basic |
| 7 | speaker amp | MAX98357A, TQFN-16, **VDD on VBAT after the switch** (review P0: +5V is USB-only) | C910544 | extended |
| 8 | screen | 0.42" 72x40 I2C OLED module | — | hand-fitted 4-pin header |
| 9, 12 | battery + speaker connectors | JST PH 2-pin S2B-PH-K-S | C173752 | extended |
| 10 | power switch | MSK-12C02, **as a gate control only** (rated 50 mA, codexmb second pass): common to GND, "on" throw grounds Q1's gate; off without USB = zero drain | C431540 | extended |
| 11 | button | TS-1187A-B-A-B | C318884 | basic |
| 13 | passives | 0402/0603 R, C | basic | basic |
| 14 | GNSS antenna connector | u.FL (J3), **as drawn on the board = option B (active, cabled patch)**; deleted only if Petrus picks option A | — | — |
| 15 | antenna bias | 47 nH from VCC_RF (L1), **as drawn on the board = option B**; deleted only if Petrus picks option A (passive: patch → RF_IN matching per the ATGM336H manual, no VCC_RF feed) | — | — |
| 16 | antenna | **OPEN, Petrus picks A or B (asked 2026-09-15):** A = PULSE W3225 passive ceramic patch, 25 mm, 4 mm high, 3 dBi, 50 Ω, SMD, machine-placed (rows 14/15 then go); B = active ceramic patch on a u.FL cable, hand-fitted, board as drawn | A: C7414031 (10 in stock 15.9., $4.89) | A: extended |
| 17 | pulldowns / gate resistors | 100 k on Q3 gate, 100 k on GNSS ON/OFF, 1 M Q1 gate pull-up (4 µA on), 10 k + 100 k on the VBUS sense, 100 k on the wake line | basic | basic |

## Open decisions (petrus / claudeMB)
1. GNSS antenna: **OPEN between A (placed passive W3225) and B (active, cabled).** 18:11Z "ceramic antenna sounds good", 18:20Z "we go with ready parts"; claudemm posed A/B afterwards and holds the layout change until Petrus answers. The board is drawn as B. (was: decided v0.2, review it:) active antenna path per the ATGM336H manual (VCC_RF → 47 nH → u.FL), so the carrier needs an active ceramic patch; the alternative is the manual's passive path with an AT2659 LNA stage (C92450) in front of RF_IN, chosen if an active patch does not fit the case.
2. Speaker: size and placement (15 mm 4 Ω candidate).
3. **DECIDED by Petrus 2026-09-15 18:11Z ("Yes can have the tiny oled and ceramic antenna sounds good"): OLED on the carrier.** BOM row 8 becomes a JLCPCB-placeable part (bare 0.42" 72x40 panel + FPC connector, or a module with a placeable header); claudemm picks the LCSC numbers, layout may start.
4. Outline: teardrop from `cad/pendant.scad`, 1.0 mm board.
5. **GNSS gating (decided in v0.1, review it):** the module's ON/OFF pin (active-low shutdown) is driven from D2 instead of an external high-side MOSFET switch, and VBAT stays on 3V3 (10 µA) so every wake is a hot start (≤1 s, not 35 s). The manual does not state the shutdown current; if the bench shows more than tens of µA, the AO3401A high-side switch comes back.
7. **Connectors: DECIDED by Petrus 2026-09-16 07:25Z ("SH").** J1, J4, J5 (battery, motor, speaker) change from JST PH S2B-PH-SM4 (5.5 mm tall) to JST SH side-entry SM02B-SRSS-TB (LCSC C160402, 2.9 mm tall, 1 A/pin, AWG 28–32); the stack under and over the board becomes 2.9 + 1.0 + 3.6 = 7.5 mm and fits the 8.2–8.5 mm cavity of case 1805429. Leads ordered pre-terminated (cell with SH pigtail or PH→SH adapter; motor and speaker with SH plugs). Footprint swap, re-route, DRC and re-export = claudeMB; the Seeed Fusion quote is re-run on the final BOM before ordering.
6. **Speaker vs microSD:** the I2S amp needs three GPIOs and the only free ones are D8–D10, which the Sense board's SD slot also uses. Proposal: no SD in the pendant (the base station stores everything), amp on D8–D10. Alternative: drop the speaker (the pendant vibrates and shows text; the base station speaks).

## Assembly plan v0.4: single-sided for JLCPCB Economic (2026-09-16, claudeMB)
JLCPCB's assembly capabilities page (read 2026-09-16): **Economic PCBA = single-sided placement only**, 2/4/6 layers,
single board from 10 x 10 mm, 2 to 50 pcs; **Standard PCBA does both sides but its single-board minimum is 70 x 70 mm**,
so this 37.5 x 26.1 mm board can only be machine-assembled as a one-sided Economic order. Layout v0.4 therefore puts
every JLC-placed part on the **bottom** (30 parts, 20 BOM lines, 12 Basic + 8 Extended) and leaves the **top** to the two
castellated modules that are hand-soldered at home, U1 (XIAO, JLC consign, no stock) and U3 (ATGM336H-5N31), plus J6.
- L1, Q3, D1 moved from the top to the bottom (`gen_pcb.py`: L1 placed beside J3, the packer is bottom-only).
- J6 is no longer the JST SH connector: four 1.0 mm solder pads on the top in the tip pocket (`lib/WhereWatch.pretty/
  OLED_Pads_1x04_P1.00mm`, courtyard = pads + 0.25 mm), DNP, hand-fitted only if a 0.42" OLED flex tail is ever wanted.
  The bottom had no room for the three moved parts with the SH connector there. Schematic still names the SH part; the
  footprint is what JLC sees. The case CAD's OLED window stays off.
- Routed with freerouting 1.9.0 (`logs/freerouting-single.log`, `out/route-single.ses`): all signal nets complete;
  `close_nets.py` is NOT needed for this route (it was for the v0.3 leftovers and shorts nets if run again).
- `stitch_gnd.py` now keeps vias out of footprint keepout areas (J3's u.FL top keepout).
- DRC (KiCad 10.0.6, errors): 0 violations, 0 unconnected. 328 tracks, 113 vias, 4 layers.
- Order files: `out/wherewatch-carrier-gerbers-single.zip` (15 Gerber/drill files), `out/wherewatch-carrier-bom-jlc.csv`
  (JLC-placed lines only), `out/wherewatch-carrier-cpl-jlc-bottom.csv` (30 bottom parts, JLC columns). Full BOM with
  tiers, stock and prices: `out/wherewatch-carrier-bom.csv`; full CPL: `out/wherewatch-carrier-cpl.csv`.
- Fee estimate from JLC's published table, five boards, not a quote: Economic setup 8.18 + stencil 1.53 + 8 Extended
  feeders 24.56 + 670 joints 11.79 + X-ray on the two leadless parts up to 16.40 + parts 20.71 = about USD 83, plus the
  bare PCB (7.10 parametric) and shipping, plus five XIAO and five ATGM336H bought separately.

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
- [x] MAX98357A logic levels on a 4.2 V rail: VIH 1.3 V / VIL 0.6 V absolute (datasheet), 3.3 V I2S lines OK; SD_MODE = VDD selects the left word (firmware: mono on left)
- [x] ATGM336H active-antenna circuit needs no external DC block: the module provides antenna supply, detection and short protection internally (manual §2.7.1); only the 47 nH from VCC_RF
- [ ] I2S pins D8–D10 accepted (no microSD), decision 6
- [ ] GNSS ON/OFF gating accepted or MOSFET switch restored, decision 5
- [ ] ATGM336H nRESET left floating: manual says 不用时悬空 (leave floating when unused) — confirmed
- [ ] bench-proof on jumper wires done (ASSEMBLY.md)

## Review log
- 2026-09-09 19:06Z claudeMB (netlist read): P1 amp on USB-only +5V → **fixed** (VBAT); P2 Q3 gate floats at boot → **fixed** (R8 100 k); docs: README's "source of truth" wording vs BUILD.md's face-board table → wording fixed here, BUILD.md relabel awaits Petrus's OLED decision (bare 0.42" module on J6, purple board out).
- 2026-09-09 19:21Z codexmb full second report + claudeMB v0.3 read → **v0.3.1**: Q3 is AO3400A (RDS(on) specified at 2.5 V gate drive, 5.8 A; the 2N7002 was 115 mA and only specified at 5/10 V); IMU INT1 wired-OR onto the button line (BTN, D1) with an explicit 100 k pull-up, IMU set open-drain active-low in firmware, wake source read from WAKE_UP_SRC, so wrist-flick wake needs no extra XIAO pin; R1 1 M (4 µA while on); title block v0.3. AO3401A/AO3400A pin order 1 G, 2 S, 3 D confirmed in both the KiCad parents (TP0610T, Q_NMOS_GSD) and the AOS datasheets. Still open: no-cell USB behaviour (bench), motor stall current (needs the exact ERM part), PDF label overlap (cosmetic).
- 2026-09-09 19:16Z codexmb (second pass): MSK-12C02 is rated 12 V / 50 mA and sat in the battery path → **fixed v0.3**: it is a gate control for a 4 A P-MOSFET load switch, with a USB-present override so charging never passes through the switch; LSM6DS3 SDx/SCx must be VDDIO or GND in mode 1 → **fixed** (GND). MAX98357A VIH 1.3 V confirmed by codexmb from ADI too.
- 2026-09-09 19:07Z codexmb (independent): P0 same amp rail → fixed; P0 antenna path undocumented → **fixed** with the manual's active-antenna bias (L1 47 nH from VCC_RF); P1 ON/OFF pulldown → **fixed** (R9); P1 BUILD.md D8–D10 statement → docs, with the relabel; P1 MSK-12C02 pad 2 = common → still **[verify]** against the manufacturer drawing before layout; P1 GNSS shutdown current → bench measurement, on the checklist. Note from codexmb worth keeping: ERC cannot catch a rail that exists only on USB, because PWR_FLAG declares it powered; power-path review is a human/agent read of the netlist.

## Power budget (quiescent, carrier only)

| item | current | when |
|---|---|---|
| R1 gate pull-up (1 M from the cell) | ~4 µA | switch on |
| R6/R7 battery divider (200 k) | ~20 µA | switch on |
| R10 VBUS sense | 0 | no USB |
| GNSS off (ON/OFF low) | backup only, ~10 µA (datasheet, not total shutdown; bench) | switch on |
| everything | 0 (Q1 leakage) | switch off, no USB |

No-cell behaviour: with USB but no cell, the XIAO runs from VBUS, and VBAT carries whatever the onboard charger puts out with no battery attached; the amp and divider see that. Bring-up without a cell is fine for the S3, audio only with a cell. Bench check before fabrication (codexmb).
