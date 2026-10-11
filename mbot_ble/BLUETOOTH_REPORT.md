# mBot Bluetooth implementation report

## Outcome

The mBot v1.1 / mCore v1.6 Bluetooth path was identified and verified on the
actual robot before motor-control firmware was used. The key hardware test was
a BLE-to-UART round trip: the computer wrote `PING\n` to the module and received
`PONG\r\n` back over a BLE notification. After that test passed, custom mCore
firmware was uploaded and the user confirmed that manual BLE commands moved the
motors.

The verified physical configuration was:

- Makeblock mBot v1.1, with an mCore v1.6 board based on the ATmega328P
- Official Makeblock Bluetooth module, advertised as
  `Makeblock_LE001b10674482`
- Drive motors connected to M1 and M2
- Mac computer running Python and the BLE controller

This solution does not use an ESP32 for the mBot BLE connection. The ESP32-CAM
project in the repository is separate.

## Protocol discovery and verification

The BLE protocol was not assumed from a device name or an unverified UUID. A
scanner was created to discover the advertised device, connect to it, and list
its GATT services, characteristics, and characteristic properties. The scan
of the user's module reported:

| GATT item | UUID | Observed use |
|---|---|---|
| Data service | `FFE1` | Service containing the module's data characteristics |
| Write characteristic | `FFE3` | Writable; accepts BLE writes from the controller |
| Notify characteristic | `FFE2` | Sends UART responses back to the computer as BLE notifications |
| Additional service | `FFE4` | Also reported by the scan; not used for motor commands |

The Python programs use the full Bluetooth-base UUID form for the write
characteristic (`0000ffe3-0000-1000-8000-00805f9b34fb`) and notification
characteristic (`0000ffe2-0000-1000-8000-00805f9b34fb`).

Official Makeblock iOS source code documents more than one BLE profile. It
includes a standard profile with service `FFF0`, write characteristic `FFF1`,
and notify characteristic `FFF4`, as well as an alternate profile with service
`FFE1`, write characteristic `FFE3`, and notify characteristic `FFE2`. The
source also distinguishes write-with-response and write-without-response
behavior by profile. Since these definitions do not prove which profile a
particular module revision uses, the implementation used the scanner output
from the user's actual module rather than relying on the standard profile.

The mCore's Bluetooth-module header uses the board's hardware UART (D0/RXD and
D1/TXD). Makeblock's official mBot firmware initializes that serial port at
115200 baud. These facts made a transparent serial bridge plausible but did
not prove the BLE module forwarded arbitrary bytes. A separate diagnostic was
therefore flashed first:

1. The diagnostic firmware reads serial input at 115200 baud.
2. It recognizes only the ASCII line `PING`.
3. It returns `PONG` over serial; it does not include motor-control code.
4. The BLE test subscribes to notifications on `FFE2`, writes `PING\n` to
   `FFE3`, and waits for `PONG`.
5. The actual robot returned `PONG\r\n`, verifying both the BLE-write-to-UART
   and UART-to-BLE-notification directions.

That successful round trip was the go/no-go check before motor control was
introduced.

## Motor firmware

The custom firmware uses Makeblock's `MeMCore.h` library and its `MeDCMotor`
driver, resetting motor objects for `M1` and `M2`. It reads single-byte
commands from the verified UART path:

| Byte | Behavior |
|---|---|
| `W` | Drive both motors forward |
| `S` | Drive both motors backward |
| `A` | Turn left by reversing M1 and driving M2 forward |
| `D` | Turn right by driving M1 forward and reversing M2 |
| `X` or Space | Stop both motors |
| Unknown byte | Stop both motors |

The current motor speed is 150 on the Makeblock driver's -255 through 255
range. The mCore also has a 500 ms command watchdog: when movement is active
and no further command byte arrives before the timeout, it stops both motors.
The watchdog is a communication-failure precaution, not a safety-rated stop;
the robot can still coast, slip, or move unexpectedly.

The firmware is built with PlatformIO for an Arduino Uno-compatible ATmega328P
target. The Makeblock library includes source files for other boards, including
MegaPi, that reference analog pins A8-A13. Those symbols do not exist on the
Uno target even though those board-specific sources are irrelevant to mCore.
The PlatformIO configuration defines A8-A13 as aliases 14-19 to let the
library compile for the target; it does not change the mCore hardware or the
firmware's use of M1/M2.

Uploading through USB replaces the currently installed mCore sketch. The BLE
module shares the hardware UART, so a serial monitor must be closed while
Bluetooth is in use.

## Python manual controller

The Python controller uses Bleak to scan for and connect to the Makeblock BLE
device. It writes movement bytes to `FFE3` without a GATT write response, which
matches the verified alternate module profile.

The original idea of listening for global keyboard events was not reliable on
macOS because global input monitoring can require extra macOS privacy
permissions. The implemented controller instead reads keys from its focused
interactive terminal in raw mode and restores the terminal state on exit. This
avoids Accessibility/Input Monitoring hooks:

- `W`, `A`, `S`, and `D` select movement.
- Space, `X`, or `x` selects stop.
- Escape or Ctrl-C exits.
- The selected command is resent every 100 ms while held as the current
  command, keeping the mCore watchdog refreshed.
- Disconnect, exit, or a lost command stream results in a stop write when
  possible and otherwise lets the firmware watchdog stop the motors.

The BLE controller and autonomous controller should not be run at the same
time; they compete for the same mBot BLE connection.

## Setup and operating workflow

From the repository root on macOS:

```sh
python3 -m venv mbot_ble/.venv
source mbot_ble/.venv/bin/activate
python -m pip install -r mbot_ble/requirements.txt
python -m mbot_ble.scan
```

The scan should find `Makeblock_LE001b10674482` and show the GATT table above.
After the bridge test firmware has been uploaded with PlatformIO, verify the
round trip:

```sh
python -m mbot_ble.bridge_test.verify_bridge
```

Only after the test reports a successful PING/PONG round trip, upload the motor
firmware from the repository root:

```sh
pio run -d mbot_ble/motor_firmware
pio run -d mbot_ble/motor_firmware --target upload --upload-port /dev/cu.usbserial-XXXX
```

Replace the upload-port value with the actual mCore USB serial port. Then run
the manual controller:

```sh
python -m mbot_ble.controller
```

The first motor-direction test should be done with both wheels raised and away
from hands, cables, and loose objects. Confirm the direction for each command
before placing the robot on the floor; actual left/right direction depends on
motor wiring and placement. If a direction is reversed, stop the robot and
adjust the corresponding motor signs in the firmware.

## Autonomous control added afterward

After manual BLE movement was confirmed, the repository was extended with an
optional Jetson-to-mBot autonomous pursuit path. The Jetson game sends player
coordinates over localhost UDP, and the rover uses an overhead camera and an
AprilTag to estimate its own pose before selecting the same BLE movement
commands. The game-to-rover UDP publisher, AprilTag calibration, and pursuit
logic do not change the verified BLE GATT profile or the motor command
protocol.

The autonomous system starts disarmed and requires a deliberate arm key. Its
code and tests were validated, but physical autonomous pursuit has not been
verified on the robot. Keep the wheels raised for initial tests and supervise
the rover closely; no obstacle avoidance or guaranteed edge protection is
implemented.

## Validation completed

- Discovered the actual device and inspected its GATT services and
  characteristic properties.
- Verified the actual `FFE3` write to `FFE2` notification PING/PONG round trip
  on the mCore.
- Successfully uploaded and flash-verified custom motor firmware.
- The user confirmed that manual BLE commands moved the robot.
- The subsequent code validation passed nine focused unit/integration tests
  under Python 3.12, Python compilation checks, and the autopilot CLI help
  check.
- Autonomous motor pursuit has not been physically tested.

## Primary source references

- [Makeblock iOS BLE profile declarations](https://github.com/Makeblock-official/Makeblock-App-For-iPhone/blob/824fbd68281f84d760340fdabada6673fe35b8d7/Makeblock_iphone/BLE/BLEPeripheral.h#L13-L27)
- [Makeblock iOS BLE write/notification handling](https://github.com/Makeblock-official/Makeblock-App-For-iPhone/blob/824fbd68281f84d760340fdabada6673fe35b8d7/Makeblock_iphone/BLE/BLEPeripheral.m#L158-L209)
- [Makeblock mBot firmware receive protocol](https://github.com/Makeblock-official/Makeblock-Libraries/blob/21b20bbd55bbaaaae6ac14a4580d0a238c8bbd4d/examples/Firmware_For_mBlock/mbot_firmware/mbot_firmware.ino#L218-L260)
- [Makeblock mCore library header](https://github.com/Makeblock-official/Makeblock-Libraries/blob/21b20bbd55bbaaaae6ac14a4580d0a238c8bbd4d/src/MeMCore.h#L22-L58)
- [Official mCore schematic](https://support.makeblock.com/hc/article_attachments/4412894400407/mcore_Mcore.png)
