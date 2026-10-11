# ESP32-CAM rover camera

PlatformIO Arduino firmware for the AI Thinker ESP32-CAM. The board hosts a
dashboard at `http://<board-ip>/` and an MJPEG stream at
`http://<board-ip>:81/stream`.

## Configure Wi-Fi

From this folder, make a local credentials header:

```sh
cp include/secrets.h.example include/secrets.h
```

Edit `include/secrets.h` with the 2.4 GHz Wi-Fi network name and password. The
file is ignored by Git. The ESP32-CAM and the device viewing the stream must be
connected to the same local network. Do not put credentials in source control.

## Build, flash, and monitor

Install PlatformIO Core or the PlatformIO IDE extension, connect the ESP32-CAM
programmer/USB adapter, then run these commands from `esp32_cam/`:

```sh
pio run
pio run --target upload
pio device monitor --baud 115200
```

The AI Thinker ESP32-CAM generally needs GPIO 0 held to GND while resetting to
enter its serial bootloader. Disconnect GPIO 0 from GND and reset again after
uploading. Board adapters vary; verify their wiring and 5 V supply before
connecting the camera board.

After startup, use the dashboard URL printed in the serial monitor. The camera
uses VGA JPEG frames; two PSRAM frame buffers are used when PSRAM is available.
Without PSRAM it uses one DRAM frame buffer.

## Camera and network behavior

The firmware uses the AI Thinker camera pinout, connects as a Wi-Fi station,
and retries a dropped Wi-Fi connection. Camera or HTTP server initialization
errors are reported over serial. The stream is multipart MJPEG, not a video
recording or an authenticated endpoint; only use it on a trusted local network.
