// RubbleEcho ESP32-WROOM-32 manual hardware test.
//
// Onboard BOOT button: GPIO0, active LOW, internal pull-up.
// Verify this against the silkscreen on your board before wiring anything else.
// Do not drive GPIO0 as an output. Holding it LOW while the board resets
// puts the ROM in download mode. This sketch only reads the pin after startup.
//
// Serial: 115200 baud, one JSON object per line.
// Each press is a MANUAL HARDWARE TEST EVENT. It is not a physiological detection.
//
// Board: ESP32 Dev Module (or the matching ESP32-WROOM-32 board in Arduino IDE).
// Libraries: none beyond the ESP32 Arduino core.

#include <Arduino.h>

static const int BOOT_BUTTON_PIN = 0;
static const unsigned long DEBOUNCE_MS = 40;
static const char *DEVICE_ID = "esp32-wroom-32";

static uint32_t sequenceNumber = 0;
static int lastLevel = HIGH;
static int stableLevel = HIGH;
static unsigned long lastChangeMs = 0;
static bool pressed = false;

void setup() {
  Serial.begin(115200);
  pinMode(BOOT_BUTTON_PIN, INPUT_PULLUP);
  delay(200);
  lastLevel = digitalRead(BOOT_BUTTON_PIN);
  stableLevel = lastLevel;
  lastChangeMs = millis();
  Serial.println("RubbleEcho ESP32 manual hardware test ready");
}

void loop() {
  const int level = digitalRead(BOOT_BUTTON_PIN);
  const unsigned long now = millis();
  if (level != lastLevel) {
    lastLevel = level;
    lastChangeMs = now;
  }
  if ((now - lastChangeMs) < DEBOUNCE_MS || level != stableLevel) {
    if ((now - lastChangeMs) >= DEBOUNCE_MS) {
      stableLevel = level;
      const bool nowPressed = stableLevel == LOW;
      if (nowPressed && !pressed) {
        sequenceNumber += 1;
        Serial.print("{\"device_id\":\"");
        Serial.print(DEVICE_ID);
        Serial.print("\",\"event_id\":\"");
        Serial.print(DEVICE_ID);
        Serial.print("-");
        Serial.print(sequenceNumber);
        Serial.print("\",\"event_type\":\"boot_button\",\"sequence\":");
        Serial.print(sequenceNumber);
        Serial.print(",\"uptime_ms\":");
        Serial.print(now);
        Serial.println(",\"label\":\"MANUAL_HARDWARE_TEST\"}");
      }
      pressed = nowPressed;
    }
  }
}
