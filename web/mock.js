/* Mock Pi backend: same shapes as web/API.md. The app calls window.WW_API;
   this file provides it from canned data + generated SVG "photos" so the
   frontend is fully clickable before any hardware exists. When the real Pi
   backend lands it serves /api/* and app.js prefers it automatically. */

(function () {
  // Tiny inline SVG stand-in photos (no binary assets in the repo).
  function photo(label, hue) {
    const svg =
      `<svg xmlns="http://www.w3.org/2000/svg" width="520" height="390">` +
      `<rect width="100%" height="100%" fill="hsl(${hue},18%,14%)"/>` +
      `<circle cx="260" cy="165" r="86" fill="hsl(${hue},45%,32%)"/>` +
      `<text x="50%" y="88%" text-anchor="middle" fill="#d4a5e9" ` +
      `font-family="Inter,sans-serif" font-size="30">${label}</text></svg>`;
    return "data:image/svg+xml," + encodeURIComponent(svg);
  }

  const OBJECTS = [
    { name: "keys",          tags: ["keys", "home keys"],   last_place: "hallway table",  relative: "beside the bowl",        time: "17:42", hue: 280 },
    { name: "glasses case",  tags: ["glasses"],             last_place: "kitchen table",  relative: "beside coffee machine",  time: "11:35", hue: 200 },
    { name: "wallet",        tags: ["wallet"],              last_place: "desk",           relative: "on the laptop stand",    time: "09:12", hue: 30  },
    { name: "passport",      tags: ["passport", "docs"],    last_place: "bedroom shelf",  relative: "inside the blue folder", time: "Mon 20:03", hue: 140 },
    { name: "headphones",    tags: ["headphones", "audio"], last_place: "sofa",           relative: "left armrest",           time: "15:20", hue: 330 },
    { name: "power bank",    tags: ["battery", "charger"],  last_place: "backpack",       relative: "front pocket",           time: "Tue 08:44", hue: 50  },
  ];
  OBJECTS.forEach(o => { o.photo_url = photo(o.name, o.hue); });

  const TIMELINE = [
    { time: "17:42", object: "keys",         action: "placed",   place: "hallway table", relative: "beside the bowl" },
    { time: "16:58", object: "backpack",     action: "placed",   place: "hallway floor", relative: "under the coat rack" },
    { time: "15:20", object: "headphones",   action: "placed",   place: "sofa",          relative: "left armrest" },
    { time: "12:06", object: "glasses case", action: "not seen", place: "kitchen table", relative: "" },
    { time: "11:35", object: "glasses case", action: "seen",     place: "kitchen table", relative: "beside coffee machine" },
    { time: "11:32", object: "glasses case", action: "placed",   place: "kitchen table", relative: "beside coffee machine" },
    { time: "09:12", object: "wallet",       action: "placed",   place: "desk",          relative: "on the laptop stand" },
  ];
  TIMELINE.forEach(e => {
    const o = OBJECTS.find(o => o.name === e.object);
    e.photo_url = o ? o.photo_url : photo(e.object, 0);
    e.confidence = 0.9;
  });

  window.WW_API = {
    mock: true,
    async ask(q) {
      const ql = q.toLowerCase();
      const o = OBJECTS.find(o =>
        o.tags.some(t => ql.includes(t)) || ql.includes(o.name));
      if (!o) return { query: q, found: false };
      return {
        query: q, found: true, object: o.name, place: o.last_place,
        relative_position: o.relative, photo_url: o.photo_url,
        observed_at: o.time, confidence: 0.93,
      };
    },
    async objects() { return { objects: OBJECTS }; },
    async timeline() { return { day: "today", events: TIMELINE }; },
    async status() {
      return { pendant_online: true, battery_pct: 72, mode: "stream",
               last_frame_at: "just now", disk_used_gb: 3.2, retention_days: 30 };
    },
  };
})();
