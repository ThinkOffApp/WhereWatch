# Matrix web control: API contract (v1, as defined by claudeMB 2026-09-10 15:34Z)

The XIAO ESP32S3 serves `index.html` from this folder at `http://matrix.local/` on the home Wi-Fi (credentials compiled in from a local file, never in the repo). If no known Wi-Fi is in range the board opens its own network `ThinkOff-Matrix` and the page lives at `http://192.168.4.1/`. Plain HTTP, JSON replies, no auth on the LAN.

| endpoint | method | params | reply |
|---|---|---|---|
| `/` | GET | – | the page (`index.html`, ~5 KB, no external assets, works offline) |
| `/api/state` | GET | – | `{"mode":0..2,"modeName":"rainbow\|heart\|camera","brightness":1..255,"serpentine":0\|1,"color":"RRGGBB","mic":0\|1,"cam":0\|1}` |
| `/api/pixels` | GET | – | JSON array of 64 `"RRGGBB"` strings, row by row, the current frame (the page polls it twice a second for the live preview) |
| `/api/mode` | POST | `m=0..2` | the new state |
| `/api/brightness` | POST | `v=1..255` | the new state (the firmware's USB safety cap still applies on top) |
| `/api/serpentine` | POST | `v=0\|1` | the new state (panel wiring order; flip if the camera picture zigzags) |
| `/api/color` | POST | `hex=RRGGBB` | the new state; the heart's base colour |

Page behaviour: the brightness slider is shown as 1–100 % and sent as 1–255; mode buttons send 0/1/2; the double-clap and serial controls keep working and the page reflects them within 5 s. Unknown params should return HTTP 400 with `{"error":"..."}`.
