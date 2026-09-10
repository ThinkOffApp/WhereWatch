// 8x8 WS2812B matrix on the XIAO ESP32S3 Sense: three modes, button cycles them.
//   0 rainbow      : a slow rainbow walking across the grid
//   1 heart        : the ThinkOff heart in brand pink, hue cycling with the room's loudness
//                    from the Sense board's PDM microphone, a beat on every peak
//   2 camera       : the OV5640 frame shrunk to 8x8, one pixel per LED, live
// Wiring: matrix V+ -> XIAO 5V (USB power), V- -> GND, IN -> D6; button between D1 and GND.
// Brightness is capped for USB power (64 LEDs at full white would ask far more than a port gives).
// Build:  arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3:PSRAM=opi firmware/play-matrix
// Upload: arduino-cli upload -p /dev/cu.usbmodem* --fqbn esp32:esp32:XIAO_ESP32S3:PSRAM=opi firmware/play-matrix
// Serial (115200): r / h / c switch modes, s toggles serpentine wiring, digits 1-9 set brightness.
// No button needed: a DOUBLE CLAP (two sharp sounds 150-700 ms apart) also moves to the next mode.

#include <Adafruit_NeoPixel.h>
#include <ESP_I2S.h>
#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#if __has_include("wifi_secrets.h")
#include "wifi_secrets.h"
#else
#include "wifi_secrets.example.h"
#endif

// ---- matrix ----
static const int DATA_PIN = D6;
static const int BTN_PIN = D1;
static const int N = 64;
static bool serpentine = false;          // most 8x8 panels are row-major; flip with 's' if the picture zigzags
static uint8_t brightness = 24;          // of 255
Adafruit_NeoPixel px(N, DATA_PIN, NEO_GRB + NEO_KHZ800);

static int idx(int x, int y) {           // x right, y down, 0..7
  if (serpentine && (y & 1)) x = 7 - x;
  return y * 8 + x;
}

// ---- microphone (XIAO ESP32S3 Sense: PDM data GPIO41, clock GPIO42, per Seeed's mic page) ----
I2SClass I2S;
static bool micOk = false;
static float loudness = 0.0f;            // 0..1, smoothed
static float loudPeak = 0.0f;

static uint32_t lastClap = 0;            // double-clap detector: two sharp peaks 150-700 ms apart
static float prevLevel = 0.0f;
static bool clapPending = false;

static void micSample() {
  if (!micOk) return;
  long acc = 0; int n = 0;
  for (int i = 0; i < 256; i++) {
    int s = I2S.read();
    if (s == 0 && i > 8 && n == 0) break;
    acc += (long)abs(s); n++;
  }
  if (!n) return;
  float level = (float)acc / n / 4000.0f;   // rough normalisation for room sound
  if (level > 1.0f) level = 1.0f;
  loudness = loudness * 0.7f + level * 0.3f;
  loudPeak = loudPeak * 0.92f;
  if (level > loudPeak) loudPeak = level;
  // a clap: sudden jump from quiet to loud
  uint32_t now = millis();
  if (now < 2500) { prevLevel = level; return; }   // ignore the start-up transient
  if (level > 0.55f && prevLevel < 0.25f && now - lastClap > 150) {
    if (lastClap && now - lastClap < 700) { clapPending = true; lastClap = 0; }
    else lastClap = now;
  }
  if (lastClap && now - lastClap > 700) lastClap = 0;   // single clap expired
  prevLevel = level;
}

// ---- camera (pins from the esp32 core's CameraWebServer camera_pins.h, CAMERA_MODEL_XIAO_ESP32S3) ----
static bool camOk = false;
static bool camInit() {
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0; c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = 15; c.pin_d1 = 17; c.pin_d2 = 18; c.pin_d3 = 16; c.pin_d4 = 14; c.pin_d5 = 12; c.pin_d6 = 11; c.pin_d7 = 48;
  c.pin_xclk = 10; c.pin_pclk = 13; c.pin_vsync = 38; c.pin_href = 47;
  c.pin_sccb_sda = 40; c.pin_sccb_scl = 39; c.pin_pwdn = -1; c.pin_reset = -1;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_RGB565;
  c.frame_size = FRAMESIZE_96X96;        // small: 96x96 RGB565 = 18 KB per frame
  c.jpeg_quality = 12; c.fb_count = 1;
  c.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;
  if (esp_camera_init(&c) != ESP_OK) return false;
  sensor_t *s = esp_camera_sensor_get();
  if (s) { s->set_hmirror(s, 1); }       // mirror: looking at the panel feels like a mirror
  return true;
}

static void showCamera() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) return;
  int bw = fb->width / 8, bh = fb->height / 8;
  uint16_t *p = (uint16_t *)fb->buf;
  for (int gy = 0; gy < 8; gy++) for (int gx = 0; gx < 8; gx++) {
    unsigned long r = 0, g = 0, b = 0; int n = 0;
    for (int y = gy * bh; y < (gy + 1) * bh; y += 2) for (int x = gx * bw; x < (gx + 1) * bw; x += 2) {
      uint16_t v = p[y * fb->width + x];
      v = (v >> 8) | (v << 8);           // RGB565 arrives big-endian from the sensor
      r += (v >> 11) & 0x1F; g += (v >> 5) & 0x3F; b += v & 0x1F; n++;
    }
    if (!n) continue;
    px.setPixelColor(idx(gx, gy), px.Color((r / n) << 3, (g / n) << 2, (b / n) << 3));
  }
  esp_camera_fb_return(fb);
  px.show();
}

// ---- heart ----
static const uint8_t HEART[8] = {
  0b01100110,
  0b11111111,
  0b11111111,
  0b11111111,
  0b01111110,
  0b00111100,
  0b00011000,
  0b00000000,
};

// Ring index per heart pixel: 0 = outer edge ... 3 = core, drawn from the logo (pink, fuchsia, orange/yellow, lime, white centre)
static const uint8_t HEART_RING[8][8] = {
  {9,0,0,9,9,0,0,9},
  {0,1,1,0,0,1,1,0},
  {0,1,2,2,2,2,1,0},
  {0,1,2,3,3,2,1,0},
  {9,0,1,2,2,1,0,9},
  {9,9,0,1,1,0,9,9},
  {9,9,9,0,0,9,9,9},
  {9,9,9,9,9,9,9,9},
};
static uint32_t heartBase = 0xFF77FF;   // settable over the API (outer ring); the inner rings follow the logo
static uint32_t RING_COLORS[4] = {0xFF77FF, 0xFF00FF, 0xFFAA00, 0x99DD00};

static uint32_t scaleColor(uint32_t c, float k) {
  uint8_t r = ((c >> 16) & 0xFF) * k, g = ((c >> 8) & 0xFF) * k, b = (c & 0xFF) * k;
  return px.Color(r, g, b);
}

static void showHeart(uint32_t now) {
  // the whole heart breathes; sound makes it beat harder and brighter, the colours stay the logo's
  float pulse = 0.75f + 0.25f * sinf(now / 380.0f) + loudPeak * 0.35f;
  if (pulse > 1.0f) pulse = 1.0f;
  RING_COLORS[0] = heartBase;
  for (int y = 0; y < 8; y++) for (int x = 0; x < 8; x++) {
    uint8_t ring = HEART_RING[y][x];
    uint32_t c = 0;
    if (ring == 3 && ((x == 3 && y == 3) || (x == 4 && y == 3))) c = scaleColor(0xFFFFFF, pulse);   // white core
    else if (ring < 4) c = scaleColor(RING_COLORS[ring], pulse);
    px.setPixelColor(idx(x, y), px.gamma32(c));
  }
  px.show();
}

// ---- rainbow ----
static void showRainbow() {
  static uint16_t phase = 0;
  for (int y = 0; y < 8; y++) for (int x = 0; x < 8; x++) {
    px.setPixelColor(idx(x, y), px.gamma32(px.ColorHSV(phase + (x + y) * 2048)));
  }
  px.show();
  phase += 512;
}

// ---- web ----
WebServer web(80);
static bool wifiOk = false;
static const char PAGE[] PROGMEM = R"HTML(<!doctype html><meta name=viewport content="width=device-width,initial-scale=1"><title>ThinkOff Matrix</title>
<style>body{background:#0a0a0a;color:#eee;font-family:-apple-system,Helvetica,sans-serif;margin:0;padding:16px;text-align:center}
h1{color:#ff77ff;font-size:22px}button{background:#222;color:#eee;border:2px solid #ff00ff;border-radius:12px;padding:14px 18px;margin:6px;font-size:18px}
button.on{background:#ff00ff;color:#000}input[type=range]{width:80%}canvas{image-rendering:pixelated;width:240px;height:240px;border:1px solid #333;margin:12px}
label{display:block;margin-top:14px;color:#b0b0b0}</style>
<h1>ThinkOff Matrix</h1><div id=m><button onclick="set('mode?m=0')">rainbow</button><button onclick="set('mode?m=1')">heart</button><button onclick="set('mode?m=2')">camera</button></div>
<label>brightness <span id=bv></span></label><input id=b type=range min=4 max=160 oninput="set('brightness?v='+this.value)">
<label>heart colour</label><input id=c type=color value="#ff77ff" onchange="set('color?hex='+this.value.slice(1))">
<label>serpentine wiring</label><button id=s onclick="set('serpentine?v='+(st.serpentine?0:1))">flip</button>
<canvas id=cv width=8 height=8></canvas>
<script>let st={};async function set(q){await fetch('/api/'+q,{method:'POST'});load()}
async function load(){st=await (await fetch('/api/state')).json();document.querySelectorAll('#m button').forEach((b,i)=>b.className=i==st.mode?'on':'');b.value=st.brightness;bv.textContent=st.brightness;
const p=await (await fetch('/api/pixels')).json();const x=cv.getContext('2d');p.forEach((h,i)=>{x.fillStyle='#'+h;x.fillRect(i%8,(i/8)|0,1,1)})}
load();setInterval(async()=>{const p=await (await fetch('/api/pixels')).json();const x=cv.getContext('2d');p.forEach((h,i)=>{x.fillStyle='#'+h;x.fillRect(i%8,(i/8)|0,1,1)})},500)</script>)HTML";

// ---- modes ----
static int mode = 0;
static const char *MODE_NAME[3] = {"rainbow", "heart", "camera"};

static void announce() {
  Serial.printf("mode %d %s  mic=%s cam=%s serpentine=%d brightness=%d\n", mode, MODE_NAME[mode],
                micOk ? "ok" : "off", camOk ? "ok" : "off", serpentine, brightness);
}

static void indexTest() {                 // lights pixel 0..7 along the first row so the wiring order is obvious
  for (int i = 0; i < 8; i++) { px.clear(); px.setPixelColor(i, px.Color(255, 0, 180)); px.show(); delay(120); }
  px.clear(); px.show();
}

static void sendState() {
  char buf[200];
  snprintf(buf, sizeof buf, "{\"mode\":%d,\"modeName\":\"%s\",\"brightness\":%d,\"serpentine\":%d,\"color\":\"%06X\",\"mic\":%d,\"cam\":%d}",
           mode, MODE_NAME[mode], brightness, serpentine, (unsigned)heartBase, micOk, camOk);
  web.send(200, "application/json", buf);
}

static void webSetup() {
  web.on("/", []() { web.send_P(200, "text/html", PAGE); });
  web.on("/api/state", HTTP_GET, sendState);
  web.on("/api/mode", HTTP_POST, []() { int m = web.arg("m").toInt(); if (m >= 0 && m < 3) mode = m; announce(); sendState(); });
  web.on("/api/brightness", HTTP_POST, []() { int v = web.arg("v").toInt(); if (v >= 1 && v <= 255) { brightness = v; px.setBrightness(brightness); } sendState(); });
  web.on("/api/serpentine", HTTP_POST, []() { serpentine = web.arg("v").toInt() != 0; sendState(); });
  web.on("/api/color", HTTP_POST, []() { String h = web.arg("hex"); if (h.length() == 6) heartBase = strtoul(h.c_str(), nullptr, 16); sendState(); });
  web.on("/api/pixels", HTTP_GET, []() {
    String out = "["; out.reserve(64 * 9 + 2);
    for (int i = 0; i < N; i++) { uint32_t c = px.getPixelColor(i); char b[12]; snprintf(b, sizeof b, "%s\"%06X\"", i ? "," : "", (unsigned)(c & 0xFFFFFF)); out += b; }
    out += "]"; web.send(200, "application/json", out);
  });
  web.begin();
}

static void wifiSetup() {
  WiFi.mode(WIFI_STA); WiFi.setHostname("matrix");
  const char *ssids[2] = {WIFI_SSID_1, WIFI_SSID_2}; const char *pws[2] = {WIFI_PASS_1, WIFI_PASS_2};
  for (int i = 0; i < 2 && !wifiOk; i++) {
    if (!ssids[i][0]) continue;
    WiFi.begin(ssids[i], pws[i]);
    for (int t = 0; t < 40 && WiFi.status() != WL_CONNECTED; t++) delay(250);
    wifiOk = WiFi.status() == WL_CONNECTED;
  }
  if (!wifiOk) { WiFi.mode(WIFI_AP); WiFi.softAP("ThinkOff-Matrix"); }
  MDNS.begin("matrix");
  Serial.printf("wifi %s ip %s\n", wifiOk ? "joined" : "own network ThinkOff-Matrix", wifiOk ? WiFi.localIP().toString().c_str() : WiFi.softAPIP().toString().c_str());
  webSetup();
}

void setup() {
  Serial.begin(115200);
  pinMode(BTN_PIN, INPUT_PULLUP);
  px.begin(); px.setBrightness(brightness); px.clear(); px.show();
  I2S.setPinsPdmRx(42, 41);
  micOk = I2S.begin(I2S_MODE_PDM_RX, 16000, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO);
  camOk = camInit();
  indexTest();
  wifiSetup();
  announce();
}

void loop() {
  web.handleClient();
  static uint32_t lastBtn = 0; static bool btnWas = true;
  bool btn = digitalRead(BTN_PIN);
  uint32_t now = millis();
  if (btnWas && !btn && now - lastBtn > 300) { mode = (mode + 1) % 3; lastBtn = now; announce(); }
  btnWas = btn;
  micSample();
  if (clapPending) {                       // double clap = next mode, with a short white blink as the acknowledgement
    clapPending = false; mode = (mode + 1) % 3;
    px.fill(px.Color(60, 60, 60)); px.show(); delay(80);
    Serial.println("double clap");
    announce();
  }
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == 'r') mode = 0; else if (ch == 'h') mode = 1; else if (ch == 'c') mode = 2;
    else if (ch == 's') serpentine = !serpentine;
    else if (ch >= '1' && ch <= '9') { brightness = (ch - '0') * 12; px.setBrightness(brightness); }
    else continue;
    announce();
  }
  if (mode == 1) { showHeart(now); delay(20); }
  else if (mode == 2 && camOk) { showCamera(); delay(60); }
  else { showRainbow(); delay(40); }
}
