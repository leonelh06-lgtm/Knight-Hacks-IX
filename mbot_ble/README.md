# mBot BLE investigation

This folder contains a **read-only BLE scanner** and a non-motor BLE-to-UART
round-trip diagnostic. It discovers the advertised device name and prints the
GATT services and characteristic UUIDs/properties reported by the connected
module. The diagnostic writes only a `PING` line and expects a `PONG` response;
it does not move the motors.

See [BLUETOOTH_REPORT.md](BLUETOOTH_REPORT.md) for the detailed protocol
discovery, hardware verification, firmware, and controller implementation
report.

## Protocol research status

Makeblock's official iOS app source contains two BLE profiles:

| App profile | Data service | Write characteristic | Notify characteristic |
|---|---|---|---|
| Standard | `FFF0` | `FFF1` | `FFF4` |
| Alternate/dual | `FFE1` | `FFE3` | `FFE2` |

The app uses write-with-response for the standard profile and
write-without-response for the alternate profile. Those app definitions do not
identify which profile is used by every mBot Bluetooth module revision, so this
project does not assume either one; use the scanner output to verify the
connected module's actual GATT table.

Makeblock's official mBot firmware uses serial input framed as
`FF 55 len idx action device port slot data…`. Its mCore library exposes
serial-based Bluetooth support, but `MeMCore.h` alone is not a BLE GATT stack or
an automatic command parser. The reviewed sources do not establish the exact
UART mapping or baud rate for this particular Bluetooth module revision.

The actual module was discovered as `Makeblock_LE001b10674482`. Its scan showed
service `FFE1` with writable characteristic `FFE3` and notify characteristic
`FFE2`, plus a separate `FFE4` service. The non-motor verification sketch and
BLE round-trip test are in [bridge_test/](bridge_test/README.md). Only if that
test succeeds should motor firmware and the WASD controller be used.

> **Hardware verification completed on this mBot:** PlatformIO uploaded the
> diagnostic firmware successfully, and a BLE write to `FFE3` with `PING\n`
> returned `PONG\r\n` from the mCore on `FFE2`. The custom motor firmware was
> also uploaded and flash-verified; the user confirmed manual BLE commands made
> the robot move.

## Custom motor firmware and WASD controller

The firmware uses Makeblock's `MeDCMotor` driver on `M1` and `M2`. It accepts
ASCII `W`, `A`, `S`, `D`, and `X` (stop) bytes over the verified BLE-to-UART
path. The Python controller maps Space to `X` and sends the current command
every 100 ms. If updates stop for 500 ms, the firmware stops both motors.
Unknown input also stops the motors.

### Install and upload on macOS

1. Install PlatformIO Core or the PlatformIO IDE extension in VS Code.
2. Put the mBot on a stable surface with both drive wheels raised off the floor
   for the first powered test. Keep hands, cables, and loose objects away from
   the wheels.
3. Connect the mCore to the Mac by USB and identify its serial port. Close
   Arduino Serial Monitor; it would occupy the same UART used by BLE.
4. From the repository root, build and upload:

   ```sh
   pio run -d mbot_ble/motor_firmware
   pio run -d mbot_ble/motor_firmware --target upload --upload-port /dev/cu.usbserial-XXXX
   ```

   Replace the port with the mCore port shown by `pio device list`. Uploading
   replaces the bridge diagnostic firmware.

### Run the Python controller

In another VS Code terminal, from the repository root:

```sh
source mbot_ble/.venv/bin/activate
python -m pip install -r mbot_ble/requirements.txt
python -m mbot_ble.controller
```

Focus the terminal running the controller and press W/A/S/D to move; press
Space to stop. These are terminal keystrokes, not global keyboard hooks, so the
controller does not need Accessibility or Input Monitoring permission. Press
Escape or Ctrl-C to exit. Closing the app or losing BLE updates triggers the
firmware's 500 ms motor-stop watchdog. Each keypress sends one movement command;
the controller repeats the current command every 100 ms until another key or
Space is pressed. If the connection or controller stops, the watchdog stops
the motors.

The initial speed is limited to 150/255. If a wheel direction is reversed,
stop the robot and adjust the signs in the firmware before driving on the floor.
The M1/M2 left/right assignment and direction depend on the actual motor wiring;
test with the wheels raised before normal use.

## AprilTag pursuit of the projected player

The Jetson game can publish its actual player coordinates and arena dimensions
over localhost UDP. The rover process uses an overhead camera only to estimate
the mBot's pose from an AprilTag; it does not try to infer the projected sprite
or obstacles from camera pixels. Since obstacle avoidance was excluded, the
controller uses direct closed-loop pursuit and steers its aim inward near the
arena boundary rather than running A*.

Print an **AprilTag 36h11** marker and attach it flat on top of the mBot. Align
the marker's top edge with the rover's forward direction and note the marker
ID. Keep the overhead camera fixed so it sees the complete projected arena and
the marker. Camera/projector alignment is calibrated once by clicking the four
projected arena corners.

Run the game on the Jetson/projector and publish target coordinates:

```sh
python -m gesture_control --camera 0 --hand any --fullscreen --rover-udp-port 8766
```

In a second terminal, from the repository root, start the rover. This example
uses overhead camera index 1 and AprilTag ID 0; adjust both for your setup:

```sh
source mbot_ble/.venv/bin/activate
python -m mbot_ble.autopilot --camera 1 --tag-id 0 --game-state-port 8766
```

On first run, the camera window asks for four clicks: arena top-left,
top-right, bottom-right, then bottom-left. The mapping is saved to
`mbot_ble/arena_homography.json`; remove that file and restart calibration if
the camera, projector, or board moves. The chosen points should be the playable
arena border, not the screen edge.

The BLE controller begins **disarmed**. With both wheels raised and the board
clear, press **G** while the camera window is focused to arm. **X** or Space
disarms immediately; **Q** or Escape stops and disconnects. The mCore also
stops both motors if BLE commands stop for 500 ms. A paused or closed game, a
stale game feed, or a missing AprilTag commands stop. Only one program can
connect to the mBot at once; close the manual WASD controller before starting
the autopilot.

Pursuit steering, tag orientation, speed, board traction, and edge behavior
still need physical validation. The firmware's initial speed is 150/255; keep
the wheels lifted for the first test and test on a clear floor after verifying
turn directions. Camera-to-game calibration and motor feedback do not guarantee
collision avoidance or prevent overrunning an edge if the robot coasts, slips,
or the tag is occluded. Use physical bumpers/barriers or a human stop during
early trials. Do not use this as a safety-rated control system.

Sources:

- [Makeblock iOS BLEPeripheral.h](https://github.com/Makeblock-official/Makeblock-App-For-iPhone/blob/824fbd68281f84d760340fdabada6673fe35b8d7/Makeblock_iphone/BLE/BLEPeripheral.h#L13-L27)
- [Makeblock iOS BLEPeripheral.m](https://github.com/Makeblock-official/Makeblock-App-For-iPhone/blob/824fbd68281f84d760340fdabada6673fe35b8d7/Makeblock_iphone/BLE/BLEPeripheral.m#L158-L209)
- [Makeblock mBot firmware receive protocol](https://github.com/Makeblock-official/Makeblock-Libraries/blob/21b20bbd55bbaaaae6ac14a4580d0a238c8bbd4d/examples/Firmware_For_mBlock/mbot_firmware/mbot_firmware.ino#L218-L260)
- [Makeblock MeMCore.h](https://github.com/Makeblock-official/Makeblock-Libraries/blob/21b20bbd55bbaaaae6ac14a4580d0a238c8bbd4d/src/MeMCore.h#L22-L58)

## Run on macOS from the repository root

Use Python 3.10 or newer. In the VS Code terminal, from the repository root:

```sh
python3 -m venv mbot_ble/.venv
source mbot_ble/.venv/bin/activate
python -m pip install -r mbot_ble/requirements.txt
python -m mbot_ble.scan
```

Turn on the mBot and keep it near the Mac. If the device has a different
advertised name, pass a name substring:

```sh
python -m mbot_ble.scan --name Makeblock
```

On macOS, allow Bluetooth access when prompted. If discovery is empty, verify
that Bluetooth is enabled, the mBot is powered, and another app is not holding
the connection. The scanner may connect to the selected device to enumerate its
GATT table, then disconnects when it exits.
