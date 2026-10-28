#include <SoftwareSerial.h>

// Rover motor control. Pins and F/B/L/R/S behavior are the connected car.
// 'A' drives the surveyed legs. There is no ultrasonic on this rover.
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

// Manual arrows stop if no fresh letter arrives. The phone repeats while held.
const unsigned long STOP_TIMEOUT = 1600;

// Nine squares on the inner table. Start on row 1, the first square, facing the second.
// Row 1 runs left to right, row 2 right to left, row 3 left to right.
// 45 ms of drive per centimeter was timed at PWM 160. Do not replace it with a guessed speed.
const float MS_PER_CM = 45.0f;
const byte TURN_POWER = 255;
const unsigned long TURN_90_MS = 650;
const unsigned long DWELL_MS = 7000;
// Inner table is 101 cm by 76 cm. Each of the nine squares is one third.
const float CELL_W_CM = 33.7f;
const float CELL_H_CM = 25.3f;

unsigned long msForCm(float centimeters) {
  return (unsigned long)(centimeters * MS_PER_CM);
}

bool driveKnown = false;
bool driveLeft = true;
bool driveRight = true;

void stopCar() {
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);

  moving = false;
  driveKnown = false;
}

void drive(bool leftForward, bool rightForward) {
  // A repeat of the same direction only refreshes the watchdog.
  // Changing direction stops briefly so the two pairs do not fight.
  if (driveKnown && leftForward == driveLeft && rightForward == driveRight) {
    lastMoveCommand = millis();
    moving = motorSpeed > 0;
    return;
  }
  stopCar();
  delay(30);

  digitalWrite(IN1, leftForward ? HIGH : LOW);
  digitalWrite(IN2, leftForward ? LOW : HIGH);

  digitalWrite(IN3, rightForward ? HIGH : LOW);
  digitalWrite(IN4, rightForward ? LOW : HIGH);

  analogWrite(ENA, motorSpeed);
  analogWrite(ENB, motorSpeed);

  driveLeft = leftForward;
  driveRight = rightForward;
  driveKnown = true;
  moving = motorSpeed > 0;
  lastMoveCommand = millis();
}

enum StepKind : uint8_t { STEP_HOLD, STEP_ROLL, STEP_RIGHT, STEP_LEFT };

struct GridStep {
  StepKind kind;
  float centimeters;
  const char *fromId;
  const char *toId;
};

// One step at a time. loop() reads the next letter before the step can advance,
// so Stop and the arrows are never stuck behind the route.
const GridStep GRID[] = {
  {STEP_HOLD, 0, "r1c1", "r1c1"},
  {STEP_ROLL, CELL_W_CM, "r1c1", "r1c2"},
  {STEP_HOLD, 0, "r1c2", "r1c2"},
  {STEP_ROLL, CELL_W_CM, "r1c2", "r1c3"},
  {STEP_HOLD, 0, "r1c3", "r1c3"},
  {STEP_RIGHT, 0, nullptr, nullptr},
  {STEP_ROLL, CELL_H_CM, "r1c3", "r2c3"},
  {STEP_HOLD, 0, "r2c3", "r2c3"},
  {STEP_RIGHT, 0, nullptr, nullptr},
  {STEP_ROLL, CELL_W_CM, "r2c3", "r2c2"},
  {STEP_HOLD, 0, "r2c2", "r2c2"},
  {STEP_ROLL, CELL_W_CM, "r2c2", "r2c1"},
  {STEP_HOLD, 0, "r2c1", "r2c1"},
  {STEP_LEFT, 0, nullptr, nullptr},
  {STEP_ROLL, CELL_H_CM, "r2c1", "r3c1"},
  {STEP_HOLD, 0, "r3c1", "r3c1"},
  {STEP_LEFT, 0, nullptr, nullptr},
  {STEP_ROLL, CELL_W_CM, "r3c1", "r3c2"},
  {STEP_HOLD, 0, "r3c2", "r3c2"},
  {STEP_ROLL, CELL_W_CM, "r3c2", "r3c3"},
  {STEP_HOLD, 0, "r3c3", "r3c3"},
};

const byte GRID_COUNT = sizeof(GRID) / sizeof(GRID[0]);
bool gridOn = false;
byte gridIndex = 0;
unsigned long stepDeadline = 0;

void cancelGrid() {
  gridOn = false;
}

void beginGridStep() {
  if (gridIndex >= GRID_COUNT) {
    gridOn = false;
    stopCar();
    Serial.println("ACK {\"device\":\"arduino_uno\",\"status\":\"grid_done\"}");
    return;
  }
  const GridStep step = GRID[gridIndex];
  unsigned long duration = DWELL_MS;
  if (step.kind == STEP_HOLD) {
    stopCar();
    Serial.print("ACK {\"device\":\"arduino_uno\",\"cell\":\"");
    Serial.print(step.toId);
    Serial.println("\",\"phase\":\"hold\"}");
  } else if (step.kind == STEP_ROLL) {
    duration = msForCm(step.centimeters);
    Serial.print("ACK {\"device\":\"arduino_uno\",\"status\":\"moving\",\"from\":\"");
    Serial.print(step.fromId);
    Serial.print("\",\"to\":\"");
    Serial.print(step.toId);
    Serial.print("\",\"cm\":");
    Serial.print(step.centimeters, 1);
    Serial.print(",\"ms\":");
    Serial.print(duration);
    Serial.println("}");
    motorSpeed = 160;
    drive(true, true);
  } else {
    bool right = step.kind == STEP_RIGHT;
    motorSpeed = TURN_POWER;
    driveKnown = false;
    drive(right, !right);
    motorSpeed = 160;
    duration = TURN_90_MS;
  }
  stepDeadline = millis() + duration;
}

void startGrid() {
  gridOn = true;
  gridIndex = 0;
  Serial.println("ACK {\"device\":\"arduino_uno\",\"status\":\"grid_started\"}");
  beginGridStep();
}

void handleCommand(char command) {
  if (command >= 'a' && command <= 'z') {
    command -= ('a' - 'A');
  }

  // Ignore terminal line endings and spaces.
  if (command == '\r' || command == '\n' || command == ' ') {
    return;
  }

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
      cancelGrid();
      motorSpeed = 160;
      drive(true, true);
      break;

    case 'B':
      cancelGrid();
      motorSpeed = 160;
      drive(false, false);
      break;

    case 'L':
      cancelGrid();
      motorSpeed = TURN_POWER;
      driveKnown = false;
      drive(false, true);
      motorSpeed = 160;
      break;

    case 'R':
      cancelGrid();
      motorSpeed = TURN_POWER;
      driveKnown = false;
      drive(true, false);
      motorSpeed = 160;
      break;

    case 'A':
      startGrid();
      break;

    case 'S':
      cancelGrid();
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
  Serial.println("Hold a direction to keep going. A starts on row 1, the first square.");
  Serial.println("Each square is its own stop: 7 seconds for signals, then the next square.");
  Serial.print("Across a row ");
  Serial.print(CELL_W_CM, 1);
  Serial.print(" cm, down to the next row ");
  Serial.print(CELL_H_CM, 1);
  Serial.print(" cm, at ");
  Serial.print(MS_PER_CM, 0);
  Serial.println(" ms/cm. No ultrasonic.");
}

void loop() {
  // One letter per pass, before the route is allowed to advance.
  char command = 0;
  if (bluetooth.available()) {
    command = bluetooth.read();
  } else if (Serial.available()) {
    command = Serial.read();
  }
  if (command != 0) {
    handleCommand(command);
  }

  if (gridOn && (long)(millis() - stepDeadline) >= 0) {
    stopCar();
    gridIndex++;
    beginGridStep();
  } else if (!gridOn && moving && millis() - lastMoveCommand >= STOP_TIMEOUT) {
    stopCar();
  }
}
