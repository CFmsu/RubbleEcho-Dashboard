// Solenoid knocker. Pin A0, 200 ms on, 200 ms off, three taps.
// Upload this to the board wired to the coil. The radar USB port is a different device.
// KNOCK runs one group. START repeats that group every 5 s. STOP drives A0 low.

#include <Arduino.h>

#define SOLENOID_PIN A0

uint16_t knock_speed = 200;          // 200 ms
uint16_t time_between_knocks = 5000; // 5 seconds
bool knocking = false;

bool wait_ms(uint16_t ms) {
  uint32_t start = millis();
  while ((uint32_t)(millis() - start) < ms) {
    if (Serial.available()) {
      return false;
    }
  }
  return true;
}

bool knock(uint16_t speed) {
  for (uint8_t tap = 0; tap < 3; tap++) {
    digitalWrite(SOLENOID_PIN, HIGH);
    if (!wait_ms(speed)) {
      digitalWrite(SOLENOID_PIN, LOW);
      return false;
    }
    digitalWrite(SOLENOID_PIN, LOW);
    if (!wait_ms(speed)) {
      return false;
    }
  }
  return true;
}

String read_line() {
  String line = Serial.readStringUntil('\n');
  line.trim();
  return line;
}

void setup() {
  pinMode(SOLENOID_PIN, OUTPUT);
  digitalWrite(SOLENOID_PIN, LOW);
  Serial.begin(115200);
  Serial.setTimeout(20);
  Serial.println("ACK {\"device\":\"arduino_solenoid\",\"pin\":\"A0\",\"status\":\"ready\"}");
}

void loop() {
  if (Serial.available()) {
    String line = read_line();
    if (line == "STOP") {
      knocking = false;
      digitalWrite(SOLENOID_PIN, LOW);
      Serial.println("ACK {\"device\":\"arduino_solenoid\",\"status\":\"stopped\"}");
    } else if (line == "KNOCK") {
      bool finished = knock(knock_speed);
      digitalWrite(SOLENOID_PIN, LOW);
      Serial.println(finished
        ? "ACK {\"device\":\"arduino_solenoid\",\"status\":\"knocked\"}"
        : "ACK {\"device\":\"arduino_solenoid\",\"status\":\"stopped\"}");
    } else if (line == "START") {
      knocking = true;
      Serial.println("ACK {\"device\":\"arduino_solenoid\",\"status\":\"started\"}");
    }
  }

  if (!knocking) {
    return;
  }
  if (!wait_ms(time_between_knocks)) {
    String line = read_line();
    if (line == "STOP" || line == "") {
      knocking = false;
      digitalWrite(SOLENOID_PIN, LOW);
      return;
    }
    if (line == "KNOCK") {
      knock(knock_speed);
      digitalWrite(SOLENOID_PIN, LOW);
    }
    return;
  }
  knock(knock_speed);
}
