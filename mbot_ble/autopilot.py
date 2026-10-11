"""Pursue the projected game character using an overhead AprilTag and BLE."""

import argparse
import asyncio
import json
import math
from pathlib import Path
import socket
import time

import cv2
import numpy as np
from bleak import BleakClient

from mbot_ble.arena import (
    AprilTagTracker,
    ArenaCalibrationError,
    calibrate_camera_to_arena,
    load_homography,
)
from mbot_ble.autonomy import (
    FORWARD,
    STOP,
    TURN_LEFT,
    TURN_RIGHT,
    Pose,
    pursuit_command,
)
from mbot_ble.scan import DEFAULT_NAME, scan_and_select

WRITE_CHARACTERISTIC = "0000ffe3-0000-1000-8000-00805f9b34fb"
HEARTBEAT_SECONDS = 0.1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default=DEFAULT_NAME)
    parser.add_argument("--ble-timeout", type=float, default=15.0)
    parser.add_argument("--camera", default="1", help="Overhead camera index or device path")
    parser.add_argument("--tag-id", type=int, required=True, help="AprilTag 36h11 ID mounted on the rover")
    parser.add_argument("--game-state-port", type=int, default=8766)
    parser.add_argument(
        "--calibration",
        type=Path,
        default=Path("mbot_ble/arena_homography.json"),
    )
    parser.add_argument("--stop-distance", type=float, default=32.0)
    parser.add_argument("--boundary-margin", type=float, default=42.0)
    parser.add_argument("--game-state-timeout", type=float, default=0.5)
    args = parser.parse_args()
    if args.ble_timeout <= 0 or args.game_state_timeout <= 0:
        parser.error("timeouts must be greater than zero")
    if not 0 <= args.tag_id <= 586:
        parser.error("AprilTag 36h11 ID must be in the range 0 through 586")
    if not 1 <= args.game_state_port <= 65535:
        parser.error("game-state-port must be between 1 and 65535")
    if args.stop_distance < 0 or args.boundary_margin <= 0:
        parser.error("stop-distance must be nonnegative and boundary-margin positive")
    return args


def receive_latest_game_state(receiver: socket.socket) -> dict[str, object] | None:
    latest = None
    while True:
        try:
            raw, _address = receiver.recvfrom(2048)
        except BlockingIOError:
            break
        try:
            packet = json.loads(raw)
            x, y = float(packet["x"]), float(packet["y"])
            width, height = float(packet["width"]), float(packet["height"])
            timestamp = float(packet["timestamp"])
            if (
                packet.get("type") != "game_state"
                or not all(math.isfinite(value) for value in (x, y, width, height, timestamp))
                or width <= 0
                or height <= 0
                or not isinstance(packet.get("active"), bool)
            ):
                raise ValueError("invalid game-state fields")
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            print(f"Ignoring malformed game-state datagram: {error}")
            continue
        latest = packet
    return latest


def display_command(frame: np.ndarray, pose: Pose | None, target: tuple[float, float] | None,
                    command: bytes, armed: bool, status: str) -> None:
    if pose is not None:
        height, width = frame.shape[:2]
        cv2.circle(frame, (width // 2, height // 2), 3, (255, 255, 0), -1)
        label = f"mBot arena pose: ({pose.x:.0f}, {pose.y:.0f})"
        cv2.putText(frame, label, (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    if target is not None:
        cv2.putText(frame, f"Game target: ({target[0]:.0f}, {target[1]:.0f})",
                    (12, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    action = {
        FORWARD: "FORWARD",
        TURN_LEFT: "TURN LEFT",
        TURN_RIGHT: "TURN RIGHT",
        STOP: "STOP",
    }.get(command, "STOP")
    cv2.putText(frame, f"{'ARMED' if armed else 'DISARMED'} | {action} | {status}",
                (12, frame.shape[0] - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (0, 0, 255) if armed and command != STOP else (255, 255, 255), 2)


async def run(args: argparse.Namespace) -> None:
    camera_index: int | str = int(args.camera) if args.camera.isdecimal() else args.camera
    camera = cv2.VideoCapture(camera_index)
    if not camera.isOpened():
        camera.release()
        raise RuntimeError(
            f"Cannot open overhead camera {args.camera}. Use --camera to select its device."
        )

    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.1", args.game_state_port))
    receiver.setblocking(False)
    homography = None
    tag_tracker = None
    try:
        ok, first_frame = camera.read()
        if not ok or first_frame is None:
            raise RuntimeError("Overhead camera opened but returned no frame.")
        game_state = receive_latest_game_state(receiver)
        if game_state is None:
            print(
                "Waiting for game dimensions. Start gesture_control with "
                f"--rover-udp-port {args.game_state_port}."
            )
            deadline = time.monotonic() + args.game_state_timeout
            while game_state is None and time.monotonic() < deadline:
                await asyncio.sleep(0.05)
                game_state = receive_latest_game_state(receiver)
            if game_state is None:
                raise RuntimeError("No game state received; start the game with rover UDP enabled.")

        arena_size = (int(game_state["width"]), int(game_state["height"]))
        if args.calibration.is_file():
            homography = load_homography(args.calibration, arena_size)
        else:
            print(
                "Calibrate the overhead image by clicking the projected arena corners "
                "in order: top-left, top-right, bottom-right, bottom-left."
            )
            homography = calibrate_camera_to_arena(camera, arena_size, args.calibration)
        tag_tracker = AprilTagTracker(args.tag_id, homography)
        await operate(args, camera, receiver, tag_tracker, arena_size)
    finally:
        receiver.close()
        camera.release()
        cv2.destroyAllWindows()


async def operate(args: argparse.Namespace, camera: cv2.VideoCapture,
                  receiver: socket.socket, tag_tracker: AprilTagTracker,
                  arena_size: tuple[int, int]) -> None:
    device = await scan_and_select(args.name, args.ble_timeout)
    print("Connect the BLE controller only on this Jetson; close any other app using the mBot.")
    print("Autopilot is DISARMED. Raise the wheels; press G in the camera window to arm.")
    print("Press X to disarm, Space to pause, or Q/Escape to stop and disconnect.")
    latest_state: dict[str, object] | None = None
    last_game_state_at = 0.0
    armed = False
    current_command = STOP
    window_name = "mBot AprilTag pursuit"
    cv2.namedWindow(window_name)
    async with BleakClient(device, timeout=20) as client:
        if not client.is_connected:
            raise RuntimeError("BLE connection did not become active.")
        print(f"BLE connected to {device.name or device.address}.")
        try:
            while True:
                now = time.monotonic()
                received = receive_latest_game_state(receiver)
                if received is not None:
                    latest_state = received
                    last_game_state_at = now

                ok, frame = camera.read()
                if not ok or frame is None:
                    current_command = STOP
                    await client.write_gatt_char(WRITE_CHARACTERISTIC, STOP, response=False)
                    raise RuntimeError("Overhead camera stopped returning frames.")

                pose, corners = tag_tracker.detect(frame)
                if corners is not None:
                    cv2.aruco.drawDetectedMarkers(frame, [corners.reshape(1, 4, 2)])
                target = None
                status = "waiting for game"
                state_fresh = (
                    latest_state is not None
                    and now - last_game_state_at <= args.game_state_timeout
                )
                if state_fresh and latest_state is not None:
                    target = (float(latest_state["x"]), float(latest_state["y"]))

                game_active = (
                    state_fresh
                    and latest_state is not None
                    and latest_state["active"] is True
                )
                if not armed:
                    current_command = STOP
                    status = "press G to arm"
                elif not state_fresh:
                    current_command = STOP
                    status = "game feed stale"
                elif not game_active:
                    current_command = STOP
                    status = "game paused or inactive"
                elif pose is None:
                    current_command = STOP
                    status = "AprilTag missing or stale"
                elif target is not None:
                    current_command = pursuit_command(
                        pose, target, arena_size,
                        stop_distance=args.stop_distance,
                        boundary_margin=args.boundary_margin,
                    )
                    status = "pursuing target" if current_command != STOP else "at target / boundary"

                await client.write_gatt_char(
                    WRITE_CHARACTERISTIC, current_command, response=False
                )
                display_command(frame, pose, target, current_command, armed, status)
                cv2.imshow(window_name, frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):
                    break
                if key in (ord("g"), ord("G")):
                    armed = True
                elif key in (ord("x"), ord("X"), ord(" ")):
                    armed = False
                await asyncio.sleep(HEARTBEAT_SECONDS)
        finally:
            await client.write_gatt_char(WRITE_CHARACTERISTIC, STOP, response=False)


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nAutopilot stopped.")
    except (OSError, RuntimeError, ArenaCalibrationError) as error:
        raise SystemExit(f"mBot autopilot stopped: {error}") from error


if __name__ == "__main__":
    main()
