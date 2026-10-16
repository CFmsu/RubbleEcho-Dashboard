// RubbleEcho HC-SR04 distance sketch for an Arduino UNO R3.
//
// Do not upload this until the sensor is wired and you have set
// RUBBLEECHO_ULTRASONIC_ENABLED=true on the backend. Until then the backend
// discards distance frames. This sketch does not invent a distance when the
// echo times out.
//
// Wiring (5 V logic — UNO pins are 5 V tolerant; do not use this wiring on an ESP32):
//   HC-SR04 VCC  -> UNO 5V
//   HC-SR04 GND  -> UNO GND
//   HC-SR04 TRIG -> UNO digital pin 9
//   HC-SR04 ECHO -> UNO digital pin 8
//
// The sensor measures the round trip to a nearby exposed surface.
// It cannot detect a person through opaque rubble.
//
// Serial: 115200 baud, one JSON object per line, about 4 readings per second.

#include <Arduino.h>

static const int TRIG_PIN = 9;
static const int ECHO_PIN = 8;
static const char *DEVICE_ID = "arduino-uno-hcsr04";
static const unsigned long PULSE_TIMEOUT_US = 30000;
static uint32_t sequenceNumber = 0;

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);
  delay(50);
  Serial.println("RubbleEcho UNO HC-SR04 sketch ready");
}

void loop() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  const unsigned long duration = pulseIn(ECHO_PIN, HIGH, PULSE_TIMEOUT_US);
  sequenceNumber += 1;
  const unsigned long uptime = millis();

  Serial.print("{\"device_id\":\"");
  Serial.print(DEVICE_ID);
  Serial.print("\",\"event_id\":\"");
  Serial.print(DEVICE_ID);
  Serial.print("-");
  Serial.print(sequenceNumber);
  Serial.print("\",\"event_type\":\"distance_cm\",\"sequence\":");
  Serial.print(sequenceNumber);
  Serial.print(",\"uptime_ms\":");
  Serial.print(uptime);
  if (duration == 0) {
    Serial.println(",\"distance_cm\":null,\"valid\":false}");
  } else {
    const float centimeters = (duration * 0.0343f) / 2.0f;
    Serial.print(",\"distance_cm\":");
    Serial.print(centimeters, 1);
    Serial.println(",\"valid\":true}");
  }
  delay(250);
}
