"""Drive a Makeblock mBot with held WASD keys over its BLE UART bridge."""

import argparse
import asyncio
import os
import sys
import termios
import tty

from bleak import BleakClient
from bleak.backends.device import BLEDevice

from mbot_ble.scan import DEFAULT_NAME, scan_and_select

WRITE_CHARACTERISTIC = "0000ffe3-0000-1000-8000-00805f9b34fb"
SEND_INTERVAL_SECONDS = 0.1
STOP_COMMAND = b"X"


async def run_controller(
    device: BLEDevice, command_queue: asyncio.Queue[bytes | None]
) -> None:
    print(f"Connecting to {device.name or device.address}...")
    async with BleakClient(device, timeout=20) as client:
        if not client.is_connected:
            raise RuntimeError("BLE connection did not become active.")
        print("Connected. Focus this terminal and press W/A/S/D to move.")
        print("Press Space to stop. Press Escape or Ctrl-C to disconnect.")

        current_command = STOP_COMMAND
        try:
            while client.is_connected:
                try:
                    command = await asyncio.wait_for(
                        command_queue.get(), timeout=SEND_INTERVAL_SECONDS
                    )
                except asyncio.TimeoutError:
                    command = current_command
                else:
                    if command is None:
                        break
                    current_command = command
                await client.write_gatt_char(
                    WRITE_CHARACTERISTIC, command, response=False
                )
        finally:
            if client.is_connected:
                await client.write_gatt_char(
                    WRITE_CHARACTERISTIC, STOP_COMMAND, response=False
                )


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default=DEFAULT_NAME)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")

    device = await scan_and_select(args.name, args.timeout)
    if not sys.stdin.isatty():
        raise RuntimeError("Run the controller from an interactive VS Code terminal.")

    command_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    file_descriptor = sys.stdin.fileno()
    original_terminal_state = termios.tcgetattr(file_descriptor)

    def read_key() -> None:
        try:
            key = os.read(file_descriptor, 1)
        except BlockingIOError:
            return
        if not key:
            return
        if key in (b"\x1b", b"\x03"):
            command_queue.put_nowait(None)
            return
        if key in (b" ", b"x", b"X"):
            command_queue.put_nowait(STOP_COMMAND)
        elif key.lower() in (b"w", b"a", b"s", b"d"):
            command_queue.put_nowait(key.upper())

    try:
        tty.setraw(file_descriptor)
        loop.add_reader(file_descriptor, read_key)
        await run_controller(device, command_queue)
    finally:
        loop.remove_reader(file_descriptor)
        termios.tcsetattr(
            file_descriptor, termios.TCSADRAIN, original_terminal_state
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping controller.")
    except (OSError, RuntimeError) as error:
        raise SystemExit(f"mBot controller failed: {error}") from error
