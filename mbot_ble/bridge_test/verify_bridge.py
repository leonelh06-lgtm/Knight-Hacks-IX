"""Verify that BLE writes reach mCore UART and replies return over BLE."""

import argparse
import asyncio

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic

from mbot_ble.scan import DEFAULT_NAME, scan_and_select

WRITE_CHARACTERISTIC = "0000ffe3-0000-1000-8000-00805f9b34fb"
NOTIFY_CHARACTERISTIC = "0000ffe2-0000-1000-8000-00805f9b34fb"
RESPONSE_TIMEOUT_SECONDS = 5.0


async def verify_bridge(name: str, scan_timeout: float) -> bool:
    device = await scan_and_select(name, scan_timeout)
    response_received = asyncio.Event()
    response = bytearray()

    def notification_handler(
        _characteristic: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        response.extend(data)
        if b"PONG" in response:
            response_received.set()

    print(f"Connecting to {device.name or device.address}...")
    async with BleakClient(device, timeout=20) as client:
        if not client.is_connected:
            raise RuntimeError("BLE connection did not become active.")
        await client.start_notify(NOTIFY_CHARACTERISTIC, notification_handler)
        await client.write_gatt_char(
            WRITE_CHARACTERISTIC, b"PING\n", response=False
        )
        print("Sent the diagnostic PING; waiting for PONG...")

        try:
            await asyncio.wait_for(
                response_received.wait(), timeout=RESPONSE_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            print(
                "No PONG received. BLE-to-UART forwarding is not verified; "
                "no motor commands were sent."
            )
            return False

        print(f"Received BLE notification bytes: {bytes(response)!r}")
        print("BLE-to-UART round trip verified.")
        return True


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default=DEFAULT_NAME)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")

    return 0 if await verify_bridge(args.name, args.timeout) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        raise SystemExit("\nBLE bridge test cancelled.")
    except (OSError, RuntimeError) as error:
        raise SystemExit(f"BLE bridge test failed: {error}") from error
