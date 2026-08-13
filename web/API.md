# WhereWatch web app <-> Pi API (design contract)

The web app is static files served by the Pi. It talks to these endpoints;
until the backend exists, `mock.js` serves the same shapes from canned data
(the app auto-falls-back when `/api/*` is unreachable).

- `GET /api/ask?q=keys` -> `{query, found, object, place, relative_position,
  photo_url, observed_at, confidence}`
- `GET /api/timeline?day=2026-08-13` -> `{day, events: [{time, object,
  action, place, relative_position, photo_url, confidence}]}`
- `GET /api/objects` -> `{objects: [{name, last_place, last_seen, photo_url,
  pin: {kind: "place"|"gps", place?, lat?, lon?}}]}`  (Map tab feeds on this)
- `GET /api/status` -> `{pendant_online, battery_pct, mode: "stream"|"stills",
  last_frame_at, disk_used_gb, retention_days}`
- `POST /api/retention {days}` -> `{ok}`  (delete-older-than control)

All photo URLs are Pi-local paths. Nothing here ever points off-host.
