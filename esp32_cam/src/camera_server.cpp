#include "camera_server.h"

#include <Arduino.h>
#include <esp_http_server.h>
#include "esp_camera.h"

namespace {

constexpr char STREAM_CONTENT_TYPE[] = "multipart/x-mixed-replace;boundary=frame";
constexpr char STREAM_BOUNDARY[] = "\r\n--frame\r\n";
constexpr char STREAM_PART_HEADER[] =
    "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

httpd_handle_t dashboardServer = nullptr;
httpd_handle_t streamServer = nullptr;

constexpr char DASHBOARD_HTML[] = R"html(
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>KnightHacks IX Rover Camera</title>
  <style>
    body { margin: 0; padding: 2rem; background: #101820; color: #f2f4f8;
      font: 16px system-ui, sans-serif; text-align: center; }
    img { display: block; width: min(100%, 800px); height: auto; margin: 1rem auto;
      border-radius: 8px; background: #000; }
    a { color: #76d7c4; }
  </style>
</head>
<body>
  <h1>KnightHacks IX Rover Camera</h1>
  <img id="stream" alt="Live ESP32-CAM stream">
  <p><a id="stream-link">Open the MJPEG stream directly</a></p>
  <script>
    const url = `http://${location.hostname}:81/stream`;
    document.getElementById("stream").src = url;
    document.getElementById("stream-link").href = url;
  </script>
</body>
</html>
)html";

esp_err_t dashboardHandler(httpd_req_t *request) {
  httpd_resp_set_type(request, "text/html; charset=utf-8");
  return httpd_resp_send(request, DASHBOARD_HTML, HTTPD_RESP_USE_STRLEN);
}

esp_err_t streamHandler(httpd_req_t *request) {
  httpd_resp_set_type(request, STREAM_CONTENT_TYPE);
  httpd_resp_set_hdr(request, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(request, "Cache-Control", "no-store");

  while (true) {
    camera_fb_t *frame = esp_camera_fb_get();
    if (frame == nullptr) {
      Serial.println("Camera capture failed while streaming.");
      return ESP_FAIL;
    }

    char partHeader[64];
    const int headerLength =
        snprintf(partHeader, sizeof(partHeader), STREAM_PART_HEADER, frame->len);
    esp_err_t result = httpd_resp_send_chunk(
        request, STREAM_BOUNDARY, sizeof(STREAM_BOUNDARY) - 1);
    if (result == ESP_OK && headerLength > 0 &&
        static_cast<size_t>(headerLength) < sizeof(partHeader)) {
      result = httpd_resp_send_chunk(request, partHeader, headerLength);
    } else if (result == ESP_OK) {
      result = ESP_FAIL;
    }
    if (result == ESP_OK) {
      result = httpd_resp_send_chunk(
          request, reinterpret_cast<const char *>(frame->buf), frame->len);
    }
    esp_camera_fb_return(frame);

    if (result != ESP_OK ||
        httpd_resp_send_chunk(request, "\r\n", 2) != ESP_OK) {
      break;
    }
  }

  return ESP_OK;
}

}  // namespace

bool startCameraServer() {
  httpd_config_t dashboardConfig = HTTPD_DEFAULT_CONFIG();
  dashboardConfig.max_uri_handlers = 4;

  httpd_uri_t dashboardUri = {};
  dashboardUri.uri = "/";
  dashboardUri.method = HTTP_GET;
  dashboardUri.handler = dashboardHandler;

  esp_err_t result = httpd_start(&dashboardServer, &dashboardConfig);
  if (result != ESP_OK) {
    Serial.printf("Could not start dashboard server: 0x%x\n", result);
    dashboardServer = nullptr;
    return false;
  }

  result = httpd_register_uri_handler(dashboardServer, &dashboardUri);
  if (result != ESP_OK) {
    Serial.printf("Could not register dashboard route: 0x%x\n", result);
    httpd_stop(dashboardServer);
    dashboardServer = nullptr;
    return false;
  }

  httpd_config_t streamConfig = HTTPD_DEFAULT_CONFIG();
  streamConfig.server_port = 81;
  streamConfig.ctrl_port = 32769;
  streamConfig.max_uri_handlers = 4;
  streamConfig.stack_size = 8192;

  result = httpd_start(&streamServer, &streamConfig);
  if (result != ESP_OK) {
    Serial.printf("Could not start stream server: 0x%x\n", result);
    httpd_stop(dashboardServer);
    dashboardServer = nullptr;
    streamServer = nullptr;
    return false;
  }

  httpd_uri_t streamUri = {};
  streamUri.uri = "/stream";
  streamUri.method = HTTP_GET;
  streamUri.handler = streamHandler;

  result = httpd_register_uri_handler(streamServer, &streamUri);
  if (result != ESP_OK) {
    Serial.printf("Could not register stream route: 0x%x\n", result);
    httpd_stop(streamServer);
    httpd_stop(dashboardServer);
    streamServer = nullptr;
    dashboardServer = nullptr;
    return false;
  }

  Serial.println("HTTP dashboard and MJPEG stream servers started.");
  return true;
}
