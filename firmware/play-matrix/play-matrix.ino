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

static void showHeart(uint32_t now) {
  // ThinkOff pink at rest (hue ~ 300 degrees), sliding toward fuchsia and yellow with loudness
  uint16_t hue = 54000 - (uint16_t)(loudness * 22000.0f);
  uint8_t val = 120 + (uint8_t)(loudPeak * 135.0f);
  float pulse = 0.85f + 0.15f * sinf(now / 400.0f);
  for (int y = 0; y < 8; y++) for (int x = 0; x < 8; x++) {
    bool on = HEART[y] & (0x80 >> x);
    uint32_t c = on ? px.gamma32(px.ColorHSV(hue, 230, (uint8_t)(val * pulse))) : 0;
    px.setPixelColor(idx(x, y), c);
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

void setup() {
  Serial.begin(115200);
  pinMode(BTN_PIN, INPUT_PULLUP);
  px.begin(); px.setBrightness(brightness); px.clear(); px.show();
  I2S.setPinsPdmRx(42, 41);
  micOk = I2S.begin(I2S_MODE_PDM_RX, 16000, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO);
  camOk = camInit();
  indexTest();
  announce();
}

void loop() {
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
