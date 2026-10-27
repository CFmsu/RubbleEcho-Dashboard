#include <SoftwareSerial.h>

// Rover motor control. Pins and F/B/L/R/S behavior are the connected car.
// 'A' drives the measured 3x3 by itself. There is no ultrasonic on this rover.
// Inner table, sand_table_rev_c.json: 101 cm by 76 cm. Each cell is one third.
// 'S' from Bluetooth or USB stops the motors.

SoftwareSerial bluetooth(2, 3);  // Arduino RX = D2; TX = D3 (leave D3 disconnected)

const byte ENA = 5;
const byte IN1 = 8;
const byte IN2 = 9;
const byte IN3 = 10;
const byte IN4 = 11;
const byte ENB = 6;

int motorSpeed = 160;  // PWM: 0–255
bool moving = false;
unsigned long lastMoveCommand = 0;

// Stops after 1 second without another movement command.
const unsigned long STOP_TIMEOUT = 1000;

// Tune from one measured cell. Milliseconds of drive per centimeter at motorSpeed 160.
const float MS_PER_CM = 45.0f;
const unsigned long TURN_90_MS = 650;
const unsigned long DWELL_MS = 2000;
const float CELL_W_CM = 101.0f / 3.0f;
const float CELL_H_CM = 76.0f / 3.0f;

bool gridAborted = false;

void stopCar() {
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);

  moving = false;
}

void drive(bool leftForward, bool rightForward) {
  // Briefly disable outputs before changing direction.
  stopCar();
  delay(30);

  digitalWrite(IN1, leftForward ? HIGH : LOW);
  digitalWrite(IN2, leftForward ? LOW : HIGH);

  digitalWrite(IN3, rightForward ? HIGH : LOW);
  digitalWrite(IN4, rightForward ? LOW : HIGH);

  analogWrite(ENA, motorSpeed);
  analogWrite(ENB, motorSpeed);

  moving = motorSpeed > 0;
  lastMoveCommand = millis();
}

void handleCommand(char command);

char readPilot() {
  if (bluetooth.available()) {
    return bluetooth.read();
  }
  if (Serial.available()) {
    return Serial.read();
  }
  return 0;
}

bool waitMs(unsigned long duration) {
  unsigned long start = millis();
  while ((unsigned long)(millis() - start) < duration) {
    lastMoveCommand = millis();
    char command = readPilot();
    if (command == 0) {
      continue;
    }
    if (command == '\r' || command == '\n' || command == ' ') {
      continue;
    }
    if (command == 'S' || command == 's') {
      gridAborted = true;
      stopCar();
      return false;
    }
    gridAborted = true;
    stopCar();
    handleCommand(command);
    return false;
  }
  return true;
}

void dwell(const char *cell) {
  stopCar();
  Serial.print("ACK {\"device\":\"arduino_uno\",\"cell\":\"");
  Serial.print(cell);
  Serial.println("\",\"phase\":\"hold\"}");
  waitMs(DWELL_MS);
}

void reportMove(const char *fromCell, const char *toCell, unsigned long duration) {
  Serial.print("ACK {\"device\":\"arduino_uno\",\"status\":\"moving\",\"from\":\"");
  Serial.print(fromCell);
  Serial.print("\",\"to\":\"");
  Serial.print(toCell);
  Serial.print("\",\"ms\":");
  Serial.print(duration);
  Serial.println("}");
}

void rollCm(float centimeters) {
  if (gridAborted) {
    return;
  }
  drive(true, true);
  if (!waitMs((unsigned long)(centimeters * MS_PER_CM))) {
    return;
  }
  stopCar();
}

void travel(const char *fromCell, const char *toCell, float centimeters) {
  if (gridAborted) {
    return;
  }
  unsigned long duration = (unsigned long)(centimeters * MS_PER_CM) + 30;
  reportMove(fromCell, toCell, duration);
  rollCm(centimeters);
}

void turnRight90() {
  if (gridAborted) {
    return;
  }
  drive(true, false);  // same wheel directions as 'R'
  if (!waitMs(TURN_90_MS)) {
    return;
  }
  stopCar();
  delay(30);
}

void runMeasuredGrid() {
  // Snake over the measured cells. Row ends turn because the table measurement
  // says the row is finished, not because an ultrasonic echo arrived.
  const char *rows[3][3] = {
    {"r1c1", "r1c2", "r1c3"},
    {"r2c3", "r2c2", "r2c1"},
    {"r3c1", "r3c2", "r3c3"},
  };
  gridAborted = false;
  Serial.println("ACK {\"device\":\"arduino_uno\",\"status\":\"grid_started\"}");
  for (uint8_t row = 0; row < 3 && !gridAborted; row++) {
    dwell(rows[row][0]);
    for (uint8_t hop = 0; hop < 2 && !gridAborted; hop++) {
      travel(rows[row][hop], rows[row][hop + 1], CELL_W_CM);
      dwell(rows[row][hop + 1]);
    }
    if (row < 2 && !gridAborted) {
      const char *next = row == 0 ? "r2c3" : "r3c1";
      unsigned long rowMs = TURN_90_MS + (unsigned long)(CELL_H_CM * MS_PER_CM) + TURN_90_MS + 120;
      reportMove(rows[row][2], next, rowMs);
      turnRight90();
      rollCm(CELL_H_CM);
      turnRight90();
    }
  }
  if (!gridAborted) {
    stopCar();
    Serial.println("ACK {\"device\":\"arduino_uno\",\"status\":\"grid_done\"}");
  }
}

void handleCommand(char command) {
  if (command >= 'a' && command <= 'z') {
    command -= ('a' - 'A');
  }

  // Ignore terminal line endings and spaces.
  if (command == '\r' || command == '\n' || command == ' ') {
    return;
  }

  Serial.print("Received: ");
  Serial.println(command);

  if (command >= '0' && command <= '9') {
    motorSpeed = map(command - '0', 0, 9, 0, 255);

    // Set speed while stopped; send a direction next.
    stopCar();

    Serial.print("Speed: ");
    Serial.println(motorSpeed);
    return;
  }

  switch (command) {
    case 'F':
      drive(true, true);
      break;

    case 'B':
      drive(false, false);
      break;

    case 'L':
      drive(false, true);
      break;

    case 'R':
      drive(true, false);
      break;

    case 'A':
      runMeasuredGrid();
      break;

    case 'S':
      stopCar();
      break;

    default:
      stopCar();
      Serial.println("Unknown command: stopped");
      break;
  }
}

void setup() {
  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(ENB, OUTPUT);

  stopCar();

  Serial.begin(9600);
  bluetooth.begin(9600);  // Assumes module UART is set to 9600

  Serial.println("Ready: F B L R S A | Speed 0-9");
  Serial.println("Each movement command lasts up to 1 second. A runs the measured grid.");
}

void loop() {
  if (bluetooth.available()) {
    handleCommand(bluetooth.read());
  }

  // Also allows testing from the computer's Serial Monitor.
  if (Serial.available()) {
    handleCommand(Serial.read());
  }

  if (moving && millis() - lastMoveCommand >= STOP_TIMEOUT) {
    stopCar();
    Serial.println("Timeout: stopped");
  }
}
