/* WhereWatch web app — plain JS, zero build step.
   Talks to the Pi's /api/* (see API.md); falls back to mock.js shapes. */

const api = {
  async call(path, mockFn) {
    try {
      const r = await fetch("/api/" + path);
      if (r.ok) return await r.json();
      throw new Error(r.status);
    } catch {
      return mockFn();
    }
  },
  ask: q => api.call("ask?q=" + encodeURIComponent(q), () => WW_API.ask(q)),
  objects: () => api.call("objects", () => WW_API.objects()),
  timeline: () => api.call("timeline", () => WW_API.timeline()),
  status: () => api.call("status", () => WW_API.status()),
};

const $ = s => document.querySelector(s);

/* ---- tabs ---- */
document.querySelectorAll(".tab").forEach(t =>
  t.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(x => x.classList.toggle("active", x === t));
    document.querySelectorAll(".view").forEach(v =>
      v.classList.toggle("active", v.id === "view-" + t.dataset.view));
    if (t.dataset.view === "map") renderMap();
  }));

/* ---- device colourway themes the whole UI (petrus) ---- */
const COLORWAYS = [
  { key:"fuchsia", hex:"#d946ef" }, { key:"orange", hex:"#f97316" },
  { key:"yellow", hex:"#facc15" },  { key:"lime",   hex:"#84cc16" },
  { key:"black",  hex:"#2a2a30" },
];
(function initAccent(){
  const saved = localStorage.getItem("ww-accent") || "fuchsia";
  document.documentElement.setAttribute("data-accent", saved);
  const box = document.getElementById("swatches");
  COLORWAYS.forEach(c => {
    const b = document.createElement("button");
    b.style.background = c.hex;
    b.title = c.key + " pendant";
    b.setAttribute("aria-pressed", String(c.key === saved));
    b.addEventListener("click", () => {
      document.documentElement.setAttribute("data-accent", c.key);
      localStorage.setItem("ww-accent", c.key);
      box.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed","false"));
      b.setAttribute("aria-pressed","true");
    });
    box.appendChild(b);
  });
})();

/* ---- status pill ---- */
(async () => {
  const s = await api.status();
  $("#status-dot").classList.add(s.pendant_online ? "on" : "off");
  $("#status-text").textContent = s.pendant_online
    ? `pendant ${s.battery_pct}% · ${s.mode}` : "pendant offline";
  $("#retention-days").value = s.retention_days;
  $("#retention-label").textContent = s.retention_days + " days";
})();

/* ---- Ask: tappable object cards + free text; answers shown AND spoken ---- */
function speak(text) {
  if (!("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1.05;
  speechSynthesis.speak(u);
}

function showAnswer(a) {
  const box = $("#ask-answer");
  box.classList.remove("hidden");
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  if (!a.found) {
    box.innerHTML = `<div><div class="what">🤔 not seen recently</div>
      <div class="nope">I have no confident recent observation for “${a.query}”.
      Try the timeline, or ask again after wearing the pendant a while.</div></div>`;
    speak(`I have not seen ${a.query} recently.`);
    return;
  }
  const sentence = `Your ${a.object}: ${a.place}, ${a.relative_position}, at ${a.observed_at}.`;
  box.innerHTML = `
    <img src="${a.photo_url}" alt="last photo of ${a.object}">
    <div>
      <div class="what">${(window.WW_EMOJI && WW_EMOJI[a.object] ? WW_EMOJI[a.object]+" " : "")}${a.object}</div>
      <div class="where">📍 ${a.place} — ${a.relative_position}</div>
      <div class="when">last seen ${a.observed_at}</div>
      <div class="conf">confidence ${(a.confidence * 100).toFixed(0)}%</div>
    </div>`;
  speak(sentence);
}

$("#ask-form").addEventListener("submit", async e => {
  e.preventDefault();
  const q = $("#ask-input").value.trim();
  if (q) showAnswer(await api.ask(q));
});

/* suggested objects: photo cards + tag chips — tap to see/hear last location */
(async () => {
  const { objects } = await api.objects();
  const chips = $("#ask-chips");
  chips.innerHTML = "";
  const grid = document.createElement("div");
  grid.className = "obj-grid";
  objects.forEach(o => {
    const card = document.createElement("div");
    card.className = "obj";
    card.style.cursor = "pointer";
    card.innerHTML = `<img src="${o.photo_url}" alt="${o.name}">
      <div class="name">${o.emoji ? o.emoji + " " : ""}${o.name}</div><div class="place">${o.last_place}</div>`;
    card.addEventListener("click", async () => showAnswer(await api.ask(o.name)));
    grid.appendChild(card);
    (o.tags || []).slice(0, 1).forEach(t => {
      const b = document.createElement("button");
      b.textContent = t;
      b.addEventListener("click", async () => showAnswer(await api.ask(t)));
      chips.appendChild(b);
    });
  });
  chips.after(grid);
})();

/* ---- Did I? one-tap checks ---- */
(async () => {
  const { checks } = await api.call("checks", () => WW_API.checks());
  const grid = $("#didi-grid");
  checks.forEach(c => {
    const card = document.createElement("div");
    card.className = "obj";
    card.style.cursor = "pointer";
    card.innerHTML = `<img src="${c.photo_url}" alt="${c.label}">
      <div class="name">${c.emoji} ${c.label}</div>
      <div class="place">${c.yes ? "✓ " + c.verb + " " + c.time : "⚠ not seen today"}</div>`;
    card.addEventListener("click", () => {
      const box = $("#didi-answer");
      box.classList.remove("hidden");
      const sentence = c.yes
        ? `Yes - ${c.label} ${c.verb} at ${c.time}.`
        : `I have not seen the ${c.label.toLowerCase()} ${c.verb} today. Last: ${c.time}.`;
      box.innerHTML = `
        <img src="${c.photo_url}" alt="last photo: ${c.label}">
        <div>
          <div class="what">${c.emoji} ${c.yes ? "Yes." : "Not sure."}</div>
          <div class="where">${c.label} ${c.verb}${c.yes ? "" : "? last observation"}</div>
          <div class="when">📍 ${c.place} — ${c.time}</div>
          <div class="conf">the answer is a photo, not anxiety</div>
        </div>`;
      box.scrollIntoView({ behavior: "smooth", block: "nearest" });
      speak(sentence);
    });
    grid.appendChild(card);
  });
})();

/* ---- Timeline ---- */
(async () => {
  const { events } = await api.timeline();
  $("#timeline-list").innerHTML = events.map(e => `
    <div class="event">
      <span class="t">${e.time}</span>
      <img src="${e.photo_url}" alt="">
      <div class="desc"><b>${e.object}</b> ${e.action}
        <div class="place">📍 ${e.place}${e.relative ? " — " + e.relative : ""}</div>
      </div>
    </div>`).join("");
})();

/* ---- Map: place clusters always; Leaflet map only if GPS pins exist ---- */
let mapDone = false;
async function renderMap() {
  if (mapDone) return;
  mapDone = true;
  const { objects } = await api.objects();
  const grid = $("#map-objects");
  const places = {};
  objects.forEach(o => (places[o.last_place] ??= []).push(o));
  grid.innerHTML = Object.entries(places).map(([place, objs]) => `
    <div class="obj">
      <div class="name">📍 ${place}</div>
      ${objs.map(o => `<div class="place">· ${o.name}</div>`).join("")}
      <img src="${objs[0].photo_url}" alt="${place}">
    </div>`).join("");
  const gps = objects.filter(o => o.pin && o.pin.kind === "gps");
  const note = document.querySelector("#view-map .placeholder p");
  note.textContent = gps.length
    ? `🗺️ ${gps.length} thing(s) placed away from home.`
    : "🗺️ Everything is at a known place — GPS pins appear here when something is left away from home.";
}

/* ---- Settings ---- */
$("#retention-days").addEventListener("input", e =>
  $("#retention-label").textContent = e.target.value + " days");
$("#retention-save").addEventListener("click", async () => {
  const days = $("#retention-days").value;
  try {
    await fetch("/api/retention", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ days: +days }) });
  } catch { /* mock mode */ }
  $("#retention-save").textContent = "Saved ✓";
  setTimeout(() => $("#retention-save").textContent = "Save", 1500);
});
