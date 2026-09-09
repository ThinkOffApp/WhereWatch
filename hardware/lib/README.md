# Vendored / generated libraries

- `Seeed_XIAO.kicad_sym`, `Seeed_XIAO.pretty/XIAO-ESP32-S3-SMD.kicad_mod`: XIAO ESP32S3 symbol and footprint from Seeed Studio's OPL_Kicad_Library (https://github.com/Seeed-Studio/OPL_Kicad_Library), CC BY-SA 4.0, unmodified.
- `WhereWatch.pretty/ATGM336H-5N31.kicad_mod` and `MSK-12C02.kicad_mod`: footprints converted from the EasyEDA/LCSC part records (C90770, C431540) with easyeda2kicad; pad numbering per the manufacturers' datasheets, to be checked against them at review (JLCPCB assembles from these same records). Renamed only.
- `WhereWatch.kicad_sym`: the ATGM336H-5N31 symbol drawn by `gen_schematic.py` from the user manual §2.4.
- Everything else comes from KiCad 10's bundled libraries.
