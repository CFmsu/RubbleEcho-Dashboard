// Status-only bridge. This sketch does not invent radar, ultrasonic, or piezo values.
// A later verified build should call the Seeed MR60BHA2 library and print RADAR {json}.

void setup() {
  Serial.begin(115200);
  Serial.println("{\"device\":\"esp32\",\"status\":\"NEEDS_HARDWARE_VERIFICATION\"}");
}

void loop() {
  Serial.println("{\"device\":\"esp32\",\"status\":\"NEEDS_HARDWARE_VERIFICATION\"}");
  delay(1000);
}
