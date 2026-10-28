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

// Surveyed separations from sand_table_rev_c.json. Not equal thirds of the box.
// Near to far is 25.0 cm. A at x 52.5 to B at x 17.0 is 35.5 cm. B to C is 71.0 cm.
// Start on A_NEAR facing A_FAR, down the table. No ultrasonic.
const float SPEED_CM_S = 22.2f;
const float TURN_DEG_S = 138.5f;
const unsigned long DWELL_MS = 2000;
const float NEAR_TO_FAR_CM = 25.0f;
const float A_TO_SIDE_CM = 35.5f;
const float B_TO_C_CM = 71.0f;

unsigned long msForCm(float centimeters) {
  return (unsigned long)((centimeters / SPEED_CM_S) * 1000.0f);
}

unsigned long msForTurn90() {
  return (unsigned long)((90.0f / TURN_DEG_S) * 1000.0f);
}

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
  if (!waitMs(msForCm(centimeters))) {
    return;
  }
  stopCar();
}

void travel(const char *fromCell, const char *toCell, float centimeters) {
  if (gridAborted) {
    return;
  }
  unsigned long duration = msForCm(centimeters) + 30;
  reportMove(fromCell, toCell, duration);
  rollCm(centimeters);
}

void turnRight90() {
  if (gridAborted) {
    return;
  }
  drive(true, false);  // same wheel directions as 'R'
  if (!waitMs(msForTurn90())) {
    return;
  }
  stopCar();
  delay(30);
}

void turnLeft90() {
  if (gridAborted) {
    return;
  }
  drive(false, true);  // same wheel directions as 'L'
  if (!waitMs(msForTurn90())) {
    return;
  }
  stopCar();
  delay(30);
}

void runMeasuredGrid() {
  // Place the rover on A_NEAR, facing A_FAR. Each leg is a surveyed distance.
  gridAborted = false;
  Serial.println("ACK {\"device\":\"arduino_uno\",\"status\":\"grid_started\"}");
  dwell("A_NEAR");
  travel("A_NEAR", "A_FAR", NEAR_TO_FAR_CM);
  dwell("A_FAR");
  turnRight90();
  travel("A_FAR", "B_FAR", A_TO_SIDE_CM);
  dwell("B_FAR");
  turnLeft90();
  travel("B_FAR", "B_NEAR", NEAR_TO_FAR_CM);
  dwell("B_NEAR");
  turnLeft90();
  travel("B_NEAR", "C_NEAR", B_TO_C_CM);
  dwell("C_NEAR");
  turnRight90();
  travel("C_NEAR", "C_FAR", NEAR_TO_FAR_CM);
  dwell("C_FAR");
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
  Serial.print("Near to far ");
  Serial.print(NEAR_TO_FAR_CM, 1);
  Serial.print(" cm, A to side ");
  Serial.print(A_TO_SIDE_CM, 1);
  Serial.print(" cm, B to C ");
  Serial.print(B_TO_C_CM, 1);
  Serial.print(" cm, at ");
  Serial.print(SPEED_CM_S, 1);
  Serial.println(" cm/s. No ultrasonic.");
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
