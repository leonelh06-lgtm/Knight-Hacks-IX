"""Discover a Makeblock BLE device and print its GATT services and characteristics."""

import argparse
import asyncio
from collections.abc import Iterable

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice


DEFAULT_NAME = "Makeblock_LE001b10674482"


def device_name(device: BLEDevice, advertised_name: str | None) -> str:
    return advertised_name or device.name or "(unnamed)"


def matching_devices(
    discovered: Iterable[tuple[BLEDevice, object]], name_filter: str
) -> list[BLEDevice]:
    matches: dict[str, BLEDevice] = {}
    for device, advertisement in discovered:
        local_name = getattr(advertisement, "local_name", None)
        name = device_name(device, local_name)
        if name_filter.casefold() in name.casefold():
            matches[device.address] = device
    return list(matches.values())


async def scan_and_select(name_filter: str, timeout: float) -> BLEDevice:
    print(f"Scanning for BLE devices for {timeout:g} seconds...")
    discovered = await BleakScanner.discover(timeout=timeout, return_adv=True)
    matches = matching_devices(discovered.values(), name_filter)

    if not matches:
        print(f"No device matched '{name_filter}'. Devices seen during scan:")
        if discovered:
            for device, advertisement in discovered.values():
                name = device_name(device, getattr(advertisement, "local_name", None))
                print(f"  {name} (RSSI {advertisement.rssi} dBm)")
        else:
            print("  No BLE advertisements were received.")
        raise RuntimeError(
            f"No BLE device with '{name_filter}' in its advertised name was found. "
            "Check Bluetooth permissions and whether the mBot is advertising, "
            "then try again."
        )

    print("\nMatching devices:")
    for index, device in enumerate(matches, start=1):
        print(f"  {index}. {device.name or '(name is in advertisement data)'}")

    if len(matches) == 1:
        return matches[0]

    while True:
        choice = input(f"Select a device (1-{len(matches)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(matches):
            return matches[int(choice) - 1]
        print("Enter one of the listed numbers.")


async def print_gatt(device: BLEDevice) -> None:
    print(f"\nConnecting to {device.name or device.address}...")
    async with BleakClient(device, timeout=20) as client:
        print(f"Connected: {client.is_connected}")
        print("\nGATT services and characteristics:")
        for service in client.services:
            print(f"\nService: {service.uuid} ({service.description})")
            for characteristic in service.characteristics:
                properties = ", ".join(characteristic.properties)
                print(
                    f"  Characteristic: {characteristic.uuid}\n"
                    f"    Handle: {characteristic.handle}\n"
                    f"    Properties: {properties or '(none reported)'}"
                )
                for descriptor in characteristic.descriptors:
                    print(f"    Descriptor: {descriptor.uuid} (handle {descriptor.handle})")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--name",
        default=DEFAULT_NAME,
        help=f"substring to match in the advertised BLE name (default: {DEFAULT_NAME})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="BLE discovery duration in seconds (default: 10)",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")

    device = await scan_and_select(args.name, args.timeout)
    await print_gatt(device)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScan cancelled.")
    except (OSError, RuntimeError) as error:
        raise SystemExit(f"BLE scan failed: {error}") from error
