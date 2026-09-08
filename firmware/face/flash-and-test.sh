#!/bin/sh
# Flash the face firmware onto the ESP32-C3 OLED board over USB and prove it:
# after the upload, talk the face protocol over the same USB port and expect "pong".
# Usage: flash-and-test.sh [port]   (port defaults to the first /dev/cu.usbmodem*)
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
PORT="${1:-$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)}"
[ -n "$PORT" ] || { echo "no /dev/cu.usbmodem* port: is the display board on USB with a data cable?"; exit 2; }
FQBN="esp32:esp32:esp32c3:CDCOnBoot=cdc"
echo "port: $PORT"
arduino-cli compile --fqbn "$FQBN" "$HERE" >/dev/null
echo "compiled"
arduino-cli upload -p "$PORT" --fqbn "$FQBN" "$HERE" 2>&1 | tail -3
echo "uploaded, waiting for the board to come back"
sleep 3
PORT="$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)"
python3 - "$PORT" <<'EOF'
import sys, time, termios, os
port = sys.argv[1]
fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
attr = termios.tcgetattr(fd)
attr[0] = 0; attr[1] = 0; attr[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; attr[3] = 0
attr[4] = attr[5] = termios.B115200
termios.tcsetattr(fd, termios.TCSANOW, attr)
time.sleep(1.5)
def send(s):
    os.write(fd, (s + "\n").encode()); time.sleep(0.3)
send("#ping")
send("hello petrus")
send("#big OK")
time.sleep(1.0)
buf = b""
t0 = time.time()
while time.time() - t0 < 3:
    try:
        buf += os.read(fd, 256)
    except BlockingIOError:
        time.sleep(0.1)
os.close(fd)
text = buf.decode(errors="replace")
print("reply:", repr(text.strip()))
print("PONG OK" if "pong" in text else "NO PONG (link or firmware problem)")
EOF
