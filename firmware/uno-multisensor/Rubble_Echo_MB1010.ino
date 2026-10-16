/* Rubble Echo bench station: Uno R3 / ATmega328P, 16 MHz.
   A0 flex, A1 cavity LDR, A2 reference LDR, A3 thermistor.
   Each: 5V -> sensor -> analog node -> its own 10k resistor -> GND.
   D2/D3 PIR OUT; A4/A5 HMC6352 SDA/SCL; D8 MB1010 pin 2 PW.
   MB1010 pin 6 -> 5V, pin 7 -> GND; other pins unconnected.
   Verify actual PIR supply/pin labels and HMC6352 breakout FIRST.
   Timer1 is reserved for sonar capture: do not add Servo or D9/D10 PWM.
   Telemetry is measured input, not a survivor classifier.
*/
#include <Wire.h>
#include <util/atomic.h>

// Set true only after verifying the actual modules and their wiring.
const bool USE_PIR = false;
const bool USE_HMC6352 = false;
const uint8_t COMPASS_ADDR = 0x21;  // HMC6352 7-bit address
const uint32_t PIR_WARMUP_MS = 60000UL;

volatile uint16_t riseTicks = 0;
volatile uint16_t pulseTicks = 0;
volatile bool newPulse = false;
uint16_t pulseUs = 0;
uint32_t lastPulseMs = 0;
bool pulseSeen = false;
bool pulseValid = false;
bool compassConfigured = false;
int16_t headingTenths = -1;
uint32_t lastHeadingMs = 0;
uint32_t lastCompassPoll = 0;
uint32_t lastReport = 0;

ISR(TIMER1_CAPT_vect) {
  const uint16_t t = ICR1;
  if (TCCR1B & _BV(ICES1)) {
    riseTicks = t;
    TCCR1B &= ~_BV(ICES1);
  } else {
    pulseTicks = (uint16_t)(t - riseTicks); // handles counter wrap
    newPulse = true;
    TCCR1B |= _BV(ICES1);
  }
}

bool compassCommand(uint8_t command) {
  Wire.beginTransmission(COMPASS_ADDR);
  Wire.write(command);
  return Wire.endTransmission() == 0;
}

bool compassRAM(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(COMPASS_ADDR);
  Wire.write('G'); Wire.write(reg); Wire.write(value);
  const bool ok = Wire.endTransmission() == 0;
  delayMicroseconds(100);  // RAM write settling, no EEPROM writes
  return ok;
}

void pollCompass(uint32_t now) {
  if (!USE_HMC6352 || now - lastCompassPoll < 200UL) return;
  lastCompassPoll = now;
  if (!compassConfigured) {
    if (!compassCommand('W')) return;
    delayMicroseconds(150);
    // Standby, periodic set/reset on; force heading output in RAM only.
    compassConfigured = compassRAM(0x74, 0x50) && compassRAM(0x4E, 0x00);
    if (!compassConfigured) return;
  }
  if (!compassCommand('A')) { headingTenths = -1; return; }
  delay(7); // HMC6352 heading calculation requires at least 6 ms
  if (Wire.requestFrom(COMPASS_ADDR, (uint8_t)2) != 2) {
    headingTenths = -1;
    return;
  }
  const uint8_t hi = Wire.read();
  const uint8_t lo = Wire.read();
  const uint16_t h = ((uint16_t)hi << 8) | lo;
  if (h > 3599) { headingTenths = -1; return; }
  headingTenths = (int16_t)h;
  lastHeadingMs = millis();
}

void setup() {
  Serial.begin(115200);
  pinMode(2, INPUT); pinMode(3, INPUT); pinMode(8, INPUT);
  // 16 MHz / 64 = 250 kHz: each Timer1 tick is 4 microseconds.
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    TCCR1A = 0;
    TCCR1B = _BV(ICNC1) | _BV(ICES1) | _BV(CS11) | _BV(CS10);
    TCNT1 = 0;
    TIFR1 = _BV(ICF1);
    TIMSK1 = _BV(ICIE1);
  }
  if (USE_HMC6352) {
    Wire.begin();
    Wire.setClock(100000);
    Wire.setWireTimeout(15000, true);
  }
}

void loop() {
  const uint32_t now = millis();
  uint16_t ticks = 0;
  bool received = false;
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    if (newPulse) { ticks = pulseTicks; newPulse = false; received = true; }
  }
  if (received) {
    const uint32_t width = (uint32_t)ticks * 4UL;
    pulseValid = width >= 800UL && width <= 37520UL;
    pulseUs = pulseValid ? (uint16_t)width : 0;
    lastPulseMs = now;
    pulseSeen = true;
  }
  pollCompass(now);
  const uint32_t reportNow = millis();
  if (reportNow - lastReport < 100UL) return; // 10 telemetry rows / second
  lastReport = reportNow;
  const bool fresh = pulseSeen && pulseValid && reportNow - lastPulseMs <= 250UL;
  const float inches = pulseUs / 147.0f;
  const bool farLimit = fresh && inches >= 253.5f;
  const bool nearLimit = fresh && inches <= 6.5f;

  Serial.print(F("{\"ms\":")); Serial.print(reportNow);
  Serial.print(F(",\"flex_raw\":")); Serial.print(analogRead(A0));
  Serial.print(F(",\"light_pocket_raw\":")); Serial.print(analogRead(A1));
  Serial.print(F(",\"light_reference_raw\":")); Serial.print(analogRead(A2));
  Serial.print(F(",\"thermistor_raw\":")); Serial.print(analogRead(A3));
  Serial.print(F(",\"pir_left\":"));
  if (USE_PIR) Serial.print(digitalRead(2)); else Serial.print(F("null"));
  Serial.print(F(",\"pir_right\":"));
  if (USE_PIR) Serial.print(digitalRead(3)); else Serial.print(F("null"));
  Serial.print(F(",\"pir_ready\":"));
  Serial.print(USE_PIR && reportNow >= PIR_WARMUP_MS ? F("true") : F("false"));
  Serial.print(F(",\"heading_deg\":"));
  if (USE_HMC6352 && headingTenths >= 0 && reportNow - lastHeadingMs <= 500UL)
    Serial.print(headingTenths / 10.0f, 1);
  else Serial.print(F("null"));
  Serial.print(F(",\"range_pw_us\":"));
  if (fresh) Serial.print(pulseUs); else Serial.print(F("null"));
  Serial.print(F(",\"range_cm\":"));
  if (fresh && !farLimit) Serial.print(inches * 2.54f, 1);
  else Serial.print(F("null"));
  Serial.print(F(",\"range_status\":\""));
  if (!fresh) Serial.print(F("stale_or_invalid"));
  else if (farLimit) Serial.print(F("far_limit_or_no_echo"));
  else if (nearLimit) Serial.print(F("near_limit"));
  else Serial.print(F("ok"));
  Serial.println(F("\"}"));
}
