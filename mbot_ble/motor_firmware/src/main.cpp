#include <Arduino.h>
#include <MeMCore.h>

namespace {

constexpr unsigned long SERIAL_BAUD = 115200;
constexpr unsigned long COMMAND_TIMEOUT_MS = 500;
constexpr int16_t MOTOR_SPEED = 150;

MeDCMotor motorM1;
MeDCMotor motorM2;
unsigned long lastCommandAt = 0;
bool motorsRunning = false;

void stopMotors() {
  motorM1.run(0);
  motorM2.run(0);
  motorsRunning = false;
}

void applyCommand(char command) {
  lastCommandAt = millis();

  switch (command) {
    case 'W':
    case 'w':
      motorM1.run(MOTOR_SPEED);
      motorM2.run(MOTOR_SPEED);
      motorsRunning = true;
      break;
    case 'S':
    case 's':
      motorM1.run(-MOTOR_SPEED);
      motorM2.run(-MOTOR_SPEED);
      motorsRunning = true;
      break;
    case 'A':
    case 'a':
      motorM1.run(-MOTOR_SPEED);
      motorM2.run(MOTOR_SPEED);
      motorsRunning = true;
      break;
    case 'D':
    case 'd':
      motorM1.run(MOTOR_SPEED);
      motorM2.run(-MOTOR_SPEED);
      motorsRunning = true;
      break;
    case 'X':
    case 'x':
    case ' ':
      stopMotors();
      break;
    default:
      stopMotors();
      break;
  }
}

}  // namespace

void setup() {
  motorM1.reset(M1);
  motorM2.reset(M2);
  stopMotors();
  Serial.begin(SERIAL_BAUD);
  lastCommandAt = millis();
}

void loop() {
  while (Serial.available() > 0) {
    applyCommand(static_cast<char>(Serial.read()));
  }

  if (motorsRunning && millis() - lastCommandAt >= COMMAND_TIMEOUT_MS) {
    stopMotors();
  }
}
