#include <Arduino.h>
#include <WiFi.h>
#include "esp_camera.h"
#include "camera_server.h"

#if __has_include("secrets.h")
#include "secrets.h"
#else
#define WIFI_SSID ""
#define WIFI_PASSWORD ""
#endif

#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27

#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5

#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

namespace {

constexpr uint32_t WIFI_RETRY_INTERVAL_MS = 10000;

bool cameraReady = false;
bool serverStarted = false;
uint32_t lastWifiAttempt = 0;

bool initializeCamera() {
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_DRAM;

  if (psramFound()) {
    Serial.println("PSRAM detected.");
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    Serial.println("No PSRAM detected; using one VGA frame buffer in DRAM.");
  }

  Serial.println("Initializing AI Thinker ESP32-CAM...");
  const esp_err_t error = esp_camera_init(&config);
  if (error != ESP_OK) {
    Serial.printf("Camera initialization failed: 0x%x\n", error);
    return false;
  }

  Serial.println("Camera initialized.");
  return true;
}

void connectToWifi() {
  if (strlen(WIFI_SSID) == 0 || strlen(WIFI_PASSWORD) == 0) {
    Serial.println("Wi-Fi credentials missing. Copy include/secrets.h.example");
    Serial.println("to include/secrets.h and set your network and password.");
    return;
  }

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lastWifiAttempt = millis();
  Serial.printf("Connecting to Wi-Fi network: %s\n", WIFI_SSID);
}

}  // namespace

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  delay(1000);

  Serial.println();
  Serial.println("==========================");
  Serial.println("KNIGHTHACKS IX ROVER CAM");
  Serial.println("==========================");

  cameraReady = initializeCamera();
  if (!cameraReady) {
    Serial.println("Camera is unavailable; reboot after checking the camera module.");
    return;
  }

  connectToWifi();
}

void loop() {
  if (!cameraReady) {
    delay(1000);
    return;
  }

  if (WiFi.status() == WL_CONNECTED) {
    if (!serverStarted) {
      serverStarted = startCameraServer();
      if (serverStarted) {
        const IPAddress ip = WiFi.localIP();
        Serial.println("Camera online.");
        Serial.printf("Dashboard: http://%s/\n", ip.toString().c_str());
        Serial.printf("Live stream: http://%s:81/stream\n", ip.toString().c_str());
      }
    }
  } else if (strlen(WIFI_SSID) > 0 && strlen(WIFI_PASSWORD) > 0 &&
             millis() - lastWifiAttempt >= WIFI_RETRY_INTERVAL_MS) {
    Serial.println("Wi-Fi disconnected; retrying.");
    WiFi.reconnect();
    lastWifiAttempt = millis();
  }

  delay(250);
}
