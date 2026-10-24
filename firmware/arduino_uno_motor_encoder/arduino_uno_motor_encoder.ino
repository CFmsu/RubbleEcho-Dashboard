// RubbleEcho motor sketch. Default build does not drive the Cytron MDD10A.
// Do not upload this expecting motion. Pin numbers are not in this repository.

#ifndef PINS_VERIFIED
#define PINS_VERIFIED 0
#endif

void setup() {
  Serial.begin(115200);
  Serial.println("{\"device\":\"arduino_uno\",\"status\":\"NEEDS_HARDWARE_VERIFICATION\",\"outputs\":\"locked\"}");
}

void loop() {
  if (!PINS_VERIFIED) {
    Serial.println("{\"device\":\"arduino_uno\",\"status\":\"REFUSING_TO_DRIVE\"}");
    delay(1000);
    return;
  }
  // A verified build must include an untracked pins header and the CRC check
  // described in firmware/protocols/README.md before any PWM or DIR write.
}
