#include <Arduino.h>

constexpr unsigned long SERIAL_BAUD = 115200;
constexpr size_t INPUT_BUFFER_SIZE = 16;

char inputBuffer[INPUT_BUFFER_SIZE];
size_t inputLength = 0;

void handleInputLine() {
  inputBuffer[inputLength] = '\0';
  if (strcmp(inputBuffer, "PING") == 0) {
    Serial.println("PONG");
  }
  inputLength = 0;
}

void setup() {
  Serial.begin(SERIAL_BAUD);
}

void loop() {
  while (Serial.available() > 0) {
    const char incoming = static_cast<char>(Serial.read());

    if (incoming == '\n') {
      handleInputLine();
    } else if (incoming != '\r') {
      if (inputLength + 1 < INPUT_BUFFER_SIZE) {
        inputBuffer[inputLength++] = incoming;
      } else {
        inputLength = 0;
      }
    }
  }
}
