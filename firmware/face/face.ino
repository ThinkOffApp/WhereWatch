// WhereWatch face: the ESP32-C3 0.42" OLED board as the pendant's display + hands.
//
// The XIAO ESP32S3 (the brain) talks to this board over one UART. This board
// only draws what it is told and drives two outputs on request. No Wi-Fi, no
// logic of its own, so it can never disagree with the brain.
//
// Wiring (4 wires): XIAO 3V3 -> V3, XIAO GND -> GD, XIAO D6 (TX) -> RX,
// XIAO D7 (RX) -> TX. RX/TX on this board are GPIO20/GPIO21 (UART0 pins;
// the USB port stays free for flashing and debug).
//
// Protocol: one text line per message, newline-terminated, 115200 baud.
//   plain text        -> appended as the newest line at the bottom (scrolls, 4 lines)
//   #clear            -> blank screen
//   #big <text>       -> one line in the large font (up to 6 characters), centred
//   #vib <ms>         -> vibration motor on for <ms> milliseconds (max 2000)
//   #gps 0|1          -> GNSS power switch off/on
//   #hold             -> keep the screen on (no auto-off) until #release
//   #release          -> allow auto-off again
//   #ping             -> replies "pong" on the port the ping came from (link check)
// The screen goes dark SCREEN_TIMEOUT_MS after the last message unless held,
// and shows "no link" if the brain has been silent for LINK_TIMEOUT_MS.
//
// Board variants: the 0.42" panel sits on GPIO5/6 (01Space v1) or GPIO8/9
// (later boards). Both pairs are probed at boot for a device at 0x3C.
//
// Build (CDCOnBoot=cdc is REQUIRED: without it arduino-esp32 puts Serial on
// UART0, whose default pins on the C3 are GPIO20/21, the very pins of the
// brain link; the guard around Serial.begin() below makes a plain build
// merely lose USB debug instead of the link):
//   arduino-cli compile --fqbn esp32:esp32:esp32c3:CDCOnBoot=cdc firmware/face
// Needs the U8g2 library. Upload with the board on USB-C:
//   arduino-cli upload -p /dev/cu.usbmodem* --fqbn esp32:esp32:esp32c3:CDCOnBoot=cdc firmware/face

#include <Arduino.h>
#include <Wire.h>
#include <U8g2lib.h>

static const uint32_t BAUD = 115200;
static const int UART_RX_PIN = 20;   // header "RX"
static const int UART_TX_PIN = 21;   // header "TX"
static const int VIB_PIN = 10;       // header "10": vibration module IN
static const int GPS_EN_PIN = 3;     // header "3": GNSS power switch control
static const uint8_t OLED_ADDR = 0x3C;
static const uint32_t SCREEN_TIMEOUT_MS = 8000;
static const uint32_t LINK_TIMEOUT_MS = 60000;
static const int ROWS = 4;
static const int COLS = 12;          // 6x10 font on a 72-pixel-wide panel

HardwareSerial Brain(1);
U8G2_SSD1306_72X40_ER_F_HW_I2C *oled = nullptr;

String rows[ROWS];
String bigText;
bool screenOn = true;
bool hold = false;
uint32_t lastMsgMs = 0;
uint32_t vibUntilMs = 0;

static bool probeI2C(int sda, int scl) {
  Wire.end();
  Wire.begin(sda, scl);
  Wire.beginTransmission(OLED_ADDR);
  bool found = (Wire.endTransmission() == 0);
  return found;
}

static void initDisplay() {
  const int pairs[2][2] = {{5, 6}, {8, 9}};
  for (auto &p : pairs) {
    if (probeI2C(p[0], p[1])) {
      oled = new U8G2_SSD1306_72X40_ER_F_HW_I2C(U8G2_R0, U8X8_PIN_NONE, p[1], p[0]);
      break;
    }
  }
  if (!oled) {
    // No panel answered: still run, so the UART side and the outputs work.
    return;
  }
  oled->begin();
  oled->setBusClock(400000);
  oled->setContrast(255);
}

static void redraw() {
  if (!oled) return;
  static bool asleep = false;
  if (!screenOn) {
    if (!asleep) { oled->setPowerSave(1); asleep = true; }   // panel really off, not just black
    return;
  }
  if (asleep) { oled->setPowerSave(0); asleep = false; }
  oled->clearBuffer();
  if (bigText.length()) {
    oled->setFont(u8g2_font_logisoso16_tf);
    int w = oled->getStrWidth(bigText.c_str());
    oled->drawStr((72 - w) / 2, 30, bigText.c_str());
  } else {
    oled->setFont(u8g2_font_6x10_tf);
    for (int i = 0; i < ROWS; i++) {
      oled->drawStr(0, 9 + i * 10, rows[i].c_str());
    }
  }
  oled->sendBuffer();
}

static void pushLine(const String &s) {
  bigText = "";
  for (int i = 0; i < ROWS - 1; i++) rows[i] = rows[i + 1];
  rows[ROWS - 1] = s.substring(0, COLS);
}

static void handle(String line, Stream &from) {
  line.trim();
  if (!line.length()) return;
  lastMsgMs = millis();
  screenOn = true;
  if (line[0] != '#') {
    pushLine(line);
    redraw();
    return;
  }
  int sp = line.indexOf(' ');
  String cmd = sp < 0 ? line : line.substring(0, sp);
  String arg = sp < 0 ? "" : line.substring(sp + 1);
  arg.trim();
  if (cmd == "#clear") {
    for (auto &r : rows) r = "";
    bigText = "";
  } else if (cmd == "#big") {
    bigText = arg.substring(0, 6);
  } else if (cmd == "#vib") {
    uint32_t ms = constrain(arg.toInt(), 0, 2000);
    digitalWrite(VIB_PIN, HIGH);
    vibUntilMs = millis() + ms;
  } else if (cmd == "#gps") {
    digitalWrite(GPS_EN_PIN, arg.toInt() ? HIGH : LOW);
  } else if (cmd == "#hold") {
    hold = true;
  } else if (cmd == "#release") {
    hold = false;
  } else if (cmd == "#ping") {
    from.println("pong");              // answered where it came from (UART or USB)
  }
  redraw();
}

void setup() {
  pinMode(VIB_PIN, OUTPUT);
  digitalWrite(VIB_PIN, LOW);
  pinMode(GPS_EN_PIN, OUTPUT);
  digitalWrite(GPS_EN_PIN, LOW);      // GNSS off until the brain says otherwise
  Brain.begin(BAUD, SERIAL_8N1, UART_RX_PIN, UART_TX_PIN);
#if ARDUINO_USB_CDC_ON_BOOT
  Serial.begin(BAUD);                 // USB CDC, debug only (never UART0: that would steal GPIO20/21)
#endif
  initDisplay();
  pushLine("WhereWatch");
  pushLine(oled ? "face ready" : "no panel");
  pushLine("waiting...");
  lastMsgMs = millis();
  redraw();
}

void loop() {
  static String buf;
  while (Brain.available()) {
    char c = (char)Brain.read();
    if (c == '\n' || c == '\r') {
      if (buf.length()) handle(buf, Brain);
      buf = "";
    } else if (buf.length() < 120) {
      buf += c;
    }
  }
  // Same protocol on USB, so the face can be tried from a computer alone.
#if ARDUINO_USB_CDC_ON_BOOT
  while (Serial.available()) {
    char c = (char)Serial.read();
    static String ubuf;
    if (c == '\n' || c == '\r') {
      if (ubuf.length()) handle(ubuf, Serial);
      ubuf = "";
    } else if (ubuf.length() < 120) {
      ubuf += c;
    }
  }
#endif
  uint32_t now = millis();
  static bool linkLost = false;
  if (vibUntilMs && (int32_t)(now - vibUntilMs) >= 0) {
    digitalWrite(VIB_PIN, LOW);
    vibUntilMs = 0;
  }
  if (screenOn && !hold && !linkLost && now - lastMsgMs > SCREEN_TIMEOUT_MS) {
    screenOn = false;
    redraw();
  }
  if (!linkLost && now - lastMsgMs > LINK_TIMEOUT_MS) {
    linkLost = true;
    screenOn = true;
    pushLine("no link");
    redraw();                          // stays up: the auto-off below skips while linkLost
  } else if (linkLost && now - lastMsgMs < LINK_TIMEOUT_MS) {
    linkLost = false;                  // handle() already reset lastMsgMs on the new message
  }
  delay(5);
}
