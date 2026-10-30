#include <SoftwareSerial.h>

// Rover motor control. Pins and F/B/L/R/S behavior are the connected car.
// Both channels use the same pin polarity. A straight roll is both sides forward.
// A turn is one side forward and the other back.
// The ultrasonic, its servo, and the mmWave servo are on the Raspberry Pi.
// 'A' starts on row 1, the first square, and drives each square at the same power as forward.
// 'C' plus a cell, such as Cr2c1, is the next square. 'S' still stops.

SoftwareSerial bluetooth(2, 3);  // Arduino RX = D2; TX = D3 (leave D3 disconnected)

const byte ENA = 5;
const byte IN1 = 8;
const byte IN2 = 9;
const byte IN3 = 10;
const byte IN4 = 11;
const byte ENB = 6;

int motorSpeed = 255;  // PWM: 0–255. Full scale so the DG01D motors can turn under load.
int operatorSpeed = 255;  // Remote 0–9. Manual F B L R use this. The grid still forces full power.
bool moving = false;
unsigned long lastMoveCommand = 0;

const unsigned long STOP_TIMEOUT = 1600;
const float MS_PER_CM = 45.0f;
const byte DRIVE_POWER = 255;  // 100% PWM. The DG01D 48:1 motors stall in sand below this.
const byte TURN_POWER = 255;
const unsigned long TURN_90_MS = 650;
const unsigned long DWELL_MS = 300;
const unsigned long SWEEP_WAIT_MS = 200;
const float CELL_W_CM = 33.7f;
const float CELL_H_CM = 25.3f;

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
  if (driveKnown && leftForward == driveLeft && rightForward == driveRight) {
    analogWrite(ENA, motorSpeed);
    analogWrite(ENB, motorSpeed);
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

enum Phase : uint8_t { PHASE_IDLE, PHASE_SWEEP, PHASE_HOLD, PHASE_TURN, PHASE_ROLL, PHASE_WAIT };

Phase phase = PHASE_IDLE;
bool guided = false;
byte curRow = 0;
byte curCol = 0;
byte destRow = 0;
byte destCol = 0;
int heading = 0;
bool seen[3][3];
bool blockEast[3][3];
bool blockSouth[3][3];
bool hasQueue = false;
byte qRow = 0;
byte qCol = 0;
bool turnRight = true;
byte turnsLeft = 0;
float rollCm = 0;
unsigned long stepDeadline = 0;
bool openedListen = false;
bool readingCell = false;
char cellBuf[6];
byte cellLen = 0;

const byte PREF_R[9] = {0, 0, 0, 1, 1, 1, 2, 2, 2};
const byte PREF_C[9] = {0, 1, 2, 2, 1, 0, 0, 1, 2};

unsigned long msForCm(float centimeters) {
  return (unsigned long)(centimeters * MS_PER_CM);
}

void printCell(byte row, byte col) {
  Serial.print('r');
  Serial.print(row + 1);
  Serial.print('c');
  Serial.print(col + 1);
}

void cancelGrid() {
  guided = false;
  phase = PHASE_IDLE;
  hasQueue = false;
  readingCell = false;
}

void queueCell(const char *text) {
  if (text[0] != 'r' || text[2] != 'c' || text[4] != '\0') {
    return;
  }
  if (text[1] < '1' || text[1] > '3' || text[3] < '1' || text[3] > '3') {
    return;
  }
  byte row = text[1] - '1';
  byte col = text[3] - '1';
  if (seen[row][col]) {
    return;
  }
  if (abs((int)row - (int)curRow) + abs((int)col - (int)curCol) != 1) {
    Serial.println("ACK {\"device\":\"arduino_uno\",\"status\":\"rejected\"}");
    return;
  }
  qRow = row;
  qCol = col;
  hasQueue = true;
  if (phase == PHASE_WAIT) {
    stepDeadline = millis();
  }
}

void handleCommand(char command) {
  if (readingCell) {
    if (command == '\r' || command == '\n') {
      cellBuf[cellLen] = '\0';
      readingCell = false;
      queueCell(cellBuf);
      cellLen = 0;
      return;
    }
    if (cellLen < 4) {
      cellBuf[cellLen++] = command;
    }
    return;
  }

  if (command >= 'a' && command <= 'z') {
    command -= ('a' - 'A');
  }
  if (command == '\r' || command == '\n' || command == ' ') {
    return;
  }
  if (command >= '0' && command <= '9') {
    operatorSpeed = map(command - '0', 0, 9, 0, 255);
    motorSpeed = operatorSpeed;
    if (operatorSpeed <= 0) {
      stopCar();
    } else if (!guided && moving) {
      analogWrite(ENA, motorSpeed);
      analogWrite(ENB, motorSpeed);
      lastMoveCommand = millis();
    }
    Serial.print("Speed: ");
    Serial.println(operatorSpeed);
    return;
  }

  switch (command) {
    case 'F':
      cancelGrid();
      motorSpeed = operatorSpeed;
      drive(true, true);
      break;
    case 'B':
      cancelGrid();
      motorSpeed = operatorSpeed;
      drive(false, false);
      break;
    case 'L':
      cancelGrid();
      motorSpeed = operatorSpeed;
      driveKnown = false;
      drive(false, true);
      break;
    case 'R':
      cancelGrid();
      motorSpeed = operatorSpeed;
      driveKnown = false;
      drive(true, false);
      break;
    case 'A':
      startGrid();
      break;
    case 'C':
      readingCell = true;
      cellLen = 0;
      break;
    case 'O':
      obstacleTurn();
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

bool edgeOpen(int row, int col, int nrow, int ncol) {
  if (nrow < 0 || ncol < 0 || nrow > 2 || ncol > 2) {
    return false;
  }
  if (abs(nrow - row) + abs(ncol - col) != 1) {
    return false;
  }
  if (nrow == row && ncol == col + 1) {
    return !blockEast[row][col];
  }
  if (nrow == row && ncol == col - 1) {
    return !blockEast[nrow][ncol];
  }
  if (ncol == col && nrow == row + 1) {
    return !blockSouth[row][col];
  }
  if (ncol == col && nrow == row - 1) {
    return !blockSouth[nrow][ncol];
  }
  return false;
}

bool pickNext(byte &outRow, byte &outCol) {
  bool reached[3][3] = {};
  byte parentRow[3][3] = {};
  byte parentCol[3][3] = {};
  byte queueRow[9];
  byte queueCol[9];
  byte head = 0;
  byte tail = 0;
  reached[curRow][curCol] = true;
  queueRow[tail] = curRow;
  queueCol[tail] = curCol;
  tail++;
  const int dRow[4] = {0, 1, 0, -1};
  const int dCol[4] = {1, 0, -1, 0};
  while (head < tail) {
    byte row = queueRow[head];
    byte col = queueCol[head];
    head++;
    for (byte i = 0; i < 4; i++) {
      int nrow = (int)row + dRow[i];
      int ncol = (int)col + dCol[i];
      if (!edgeOpen(row, col, nrow, ncol) || reached[nrow][ncol]) {
        continue;
      }
      reached[nrow][ncol] = true;
      parentRow[nrow][ncol] = row;
      parentCol[nrow][ncol] = col;
      queueRow[tail] = nrow;
      queueCol[tail] = ncol;
      tail++;
    }
  }
  for (byte i = 0; i < 9; i++) {
    byte targetRow = PREF_R[i];
    byte targetCol = PREF_C[i];
    if (seen[targetRow][targetCol] || !reached[targetRow][targetCol]) {
      continue;
    }
    byte stepRow = targetRow;
    byte stepCol = targetCol;
    while (!(parentRow[stepRow][stepCol] == curRow && parentCol[stepRow][stepCol] == curCol)) {
      byte nextRow = parentRow[stepRow][stepCol];
      byte nextCol = parentCol[stepRow][stepCol];
      stepRow = nextRow;
      stepCol = nextCol;
    }
    outRow = stepRow;
    outCol = stepCol;
    return true;
  }
  return false;
}

void beginTurn() {
  // Same wheel pair as a manual L or R: one side forward, the other back.
  motorSpeed = TURN_POWER;
  driveKnown = false;
  drive(turnRight, !turnRight);
  motorSpeed = DRIVE_POWER;
  phase = PHASE_TURN;
  stepDeadline = millis() + TURN_90_MS;
  Serial.print("ACK {\"device\":\"arduino_uno\",\"status\":\"turning\",\"direction\":\"");
  Serial.print(turnRight ? "right" : "left");
  Serial.println("\"}");
}

void beginRoll() {
  unsigned long duration = msForCm(rollCm);
  Serial.print("ACK {\"device\":\"arduino_uno\",\"status\":\"moving\",\"from\":\"");
  printCell(curRow, curCol);
  Serial.print("\",\"to\":\"");
  printCell(destRow, destCol);
  Serial.print("\",\"cm\":");
  Serial.print(rollCm, 1);
  Serial.print(",\"ms\":");
  Serial.print(duration);
  Serial.println("}");
  motorSpeed = DRIVE_POWER;
  if (!(driveKnown && driveLeft && driveRight)) {
    driveKnown = false;
  }
  drive(true, true);
  phase = PHASE_ROLL;
  stepDeadline = millis() + duration;
}

void startMove(byte row, byte col) {
  int dRow = (int)row - (int)curRow;
  int dCol = (int)col - (int)curCol;
  if (abs(dRow) + abs(dCol) != 1) {
    Serial.println("ACK {\"device\":\"arduino_uno\",\"status\":\"rejected\"}");
    return;
  }
  destRow = row;
  destCol = col;
  int want = dCol == 1 ? 0 : dRow == 1 ? 90 : dCol == -1 ? 180 : 270;
  rollCm = dRow == 0 ? CELL_W_CM : CELL_H_CM;
  int delta = (want - heading + 360) % 360;
  if (delta == 0) {
    beginRoll();
    return;
  }
  turnRight = delta != 270;
  turnsLeft = delta == 180 ? 2 : 1;
  beginTurn();
}

void blockAhead() {
  if (heading == 0 && curCol < 2) {
    blockEast[curRow][curCol] = true;
  } else if (heading == 90 && curRow < 2) {
    blockSouth[curRow][curCol] = true;
  } else if (heading == 180 && curCol > 0) {
    blockEast[curRow][curCol - 1] = true;
  } else if (heading == 270 && curRow > 0) {
    blockSouth[curRow - 1][curCol] = true;
  }
}

void obstacleTurn() {
  if (!guided || phase != PHASE_ROLL) {
    return;
  }
  blockAhead();
  stopCar();
  Serial.println("ACK {\"device\":\"arduino_uno\",\"status\":\"obstacle\",\"cm\":5}");
  byte row;
  byte col;
  if (!pickNext(row, col)) {
    finishGrid();
    return;
  }
  startMove(row, col);
}

void finishGrid() {
  guided = false;
  phase = PHASE_IDLE;
  stopCar();
  Serial.println("ACK {\"device\":\"arduino_uno\",\"status\":\"grid_done\"}");
}

void publishArrived() {
  Serial.print("ACK {\"device\":\"arduino_uno\",\"status\":\"arrived\",\"cell\":\"");
  printCell(curRow, curCol);
  Serial.print("\",\"heading\":");
  Serial.print(heading);
  Serial.println("}");
}

void publishHold() {
  Serial.print("ACK {\"device\":\"arduino_uno\",\"cell\":\"");
  printCell(curRow, curCol);
  Serial.println("\",\"phase\":\"hold\"}");
}

void continueGrid() {
  byte row;
  byte col;
  if (hasQueue) {
    row = qRow;
    col = qCol;
    hasQueue = false;
  } else if (!pickNext(row, col)) {
    stopCar();
    finishGrid();
    return;
  }
  int dRow = (int)row - (int)curRow;
  int dCol = (int)col - (int)curCol;
  int want = dCol == 1 ? 0 : dRow == 1 ? 90 : dCol == -1 ? 180 : 270;
  if (want != heading) {
    stopCar();
  }
  startMove(row, col);
}

void beginVisit() {
  seen[curRow][curCol] = true;
  publishArrived();
  publishHold();
  if (!openedListen) {
    openedListen = true;
    stopCar();
    phase = PHASE_HOLD;
    stepDeadline = millis() + 12000;
    return;
  }
  continueGrid();
}

void arrive() {
  curRow = destRow;
  curCol = destCol;
  if (!seen[curRow][curCol]) {
    beginVisit();
    return;
  }
  Serial.print("ACK {\"device\":\"arduino_uno\",\"status\":\"transit\",\"cell\":\"");
  printCell(curRow, curCol);
  Serial.println("\"}");
  continueGrid();
}

void advance() {
  if (phase == PHASE_SWEEP) {
    publishHold();
    phase = PHASE_HOLD;
    stepDeadline = millis() + DWELL_MS;
    return;
  }
  if (phase == PHASE_HOLD || phase == PHASE_WAIT) {
    continueGrid();
    return;
  }
  if (phase == PHASE_TURN) {
    stopCar();
    heading = (heading + (turnRight ? 90 : 270)) % 360;
    turnsLeft--;
    if (turnsLeft > 0) {
      beginTurn();
    } else {
      beginRoll();
    }
    return;
  }
  if (phase == PHASE_ROLL) {
    arrive();
  }
}

void startGrid() {
  guided = true;
  hasQueue = false;
  readingCell = false;
  openedListen = false;
  curRow = 0;
  curCol = 0;
  heading = 0;
  memset(seen, 0, sizeof seen);
  memset(blockEast, 0, sizeof blockEast);
  memset(blockSouth, 0, sizeof blockSouth);
  Serial.println("ACK {\"device\":\"arduino_uno\",\"status\":\"grid_started\"}");
  beginVisit();
}

bool takeChar(char &out) {
  if (bluetooth.available()) {
    out = bluetooth.read();
    return true;
  }
  if (Serial.available()) {
    out = Serial.read();
    return true;
  }
  return false;
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
  bluetooth.begin(9600);

  Serial.println("Ready: F B L R S A | Speed 0-9");
  Serial.println("Hold a direction to keep going. A starts on row 1, the first square.");
  Serial.println("The Pi sweeps the ultrasonic and aims the mmWave. This board only drives.");
}

void loop() {
  char command = 0;
  if (takeChar(command)) {
    handleCommand(command);
  } else if (guided && phase != PHASE_IDLE && (long)(millis() - stepDeadline) >= 0) {
    advance();
  } else if (!guided && moving && millis() - lastMoveCommand >= STOP_TIMEOUT) {
    stopCar();
  }
}
