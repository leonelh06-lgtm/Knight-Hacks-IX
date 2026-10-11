# BLE-to-mCore bridge check

This temporary diagnostic firmware tests whether writes to the observed BLE
characteristic reach the mCore hardware UART and whether UART replies return as
BLE notifications. It accepts only the ASCII line `PING` and responds `PONG`;
it does not include or operate motor code.

The mCore is based on the ATmega328P/Arduino Uno. Makeblock's official example
firmware initializes `Serial` at 115200 baud. The mCore schematic routes its
Bluetooth-module header to D0/RXD and D1/TXD. Those facts support testing this
UART path, but do not prove the Bluetooth module bridges GATT data transparently.

References:

- [Official mCore schematic](https://support.makeblock.com/hc/article_attachments/4412894400407/mcore_Mcore.png)
- [Official mBot firmware serial setup and receive parser](https://github.com/Makeblock-official/Makeblock-Libraries/blob/21b20bbd55bbaaaae6ac14a4580d0a238c8bbd4d/examples/Firmware_For_mBlock/mbot_firmware/mbot_firmware.ino#L735-L814)
- [Official Makeblock BLE profile definitions](https://github.com/Makeblock-official/Makeblock-App-For-iPhone/blob/824fbd68281f84d760340fdabada6673fe35b8d7/Makeblock_iphone/BLE/BLEPeripheral.h#L13-L27)

## Flash with PlatformIO

From the repository root, install PlatformIO Core if needed, then:

```sh
pio run -d mbot_ble/bridge_test
pio run -d mbot_ble/bridge_test --target upload --upload-port /dev/cu.usbmodemXXXX
```

Replace the upload port with the mCore's actual USB serial port. Close any
serial monitor before using the BLE test: USB and the Bluetooth module share
the ATmega328P hardware UART. Flashing this diagnostic replaces the mBot's
current mCore firmware.

## Run the BLE round-trip test

Keep the mBot powered and run, from the repository root:

```sh
python -m mbot_ble.bridge_test.verify_bridge
```

A successful test reports that PING was written and PONG was received through
the BLE notification characteristic. If it times out, the UART bridge behavior
has not been verified, and motor control should not be added or tested yet.
After testing, reflash the final custom motor firmware before operating the
robot.
