"""AprilTag pose estimation and camera-to-game arena calibration."""

import json
from pathlib import Path

import cv2
import numpy as np

from mbot_ble.autonomy import Pose


class ArenaCalibrationError(RuntimeError):
    """Raised when arena calibration data is missing or unusable."""


def load_homography(path: Path, arena_size: tuple[int, int]) -> np.ndarray:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        matrix = np.asarray(data["homography"], dtype=np.float64)
        saved_size = (int(data["arena_width"]), int(data["arena_height"]))
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ArenaCalibrationError(f"Cannot load arena calibration {path}: {error}") from error
    if matrix.shape != (3, 3) or not np.isfinite(matrix).all():
        raise ArenaCalibrationError(f"Invalid homography matrix in {path}.")
    if saved_size != arena_size:
        raise ArenaCalibrationError(
            f"Calibration is for arena {saved_size}, but game reports {arena_size}. "
            "Remove the calibration file and recalibrate."
        )
    if abs(float(np.linalg.det(matrix))) < 1e-12:
        raise ArenaCalibrationError(f"Singular homography matrix in {path}.")
    return matrix


def save_homography(path: Path, matrix: np.ndarray, arena_size: tuple[int, int]) -> None:
    if matrix.shape != (3, 3) or not np.isfinite(matrix).all():
        raise ArenaCalibrationError("Cannot save an invalid homography matrix.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps({
        "version": 1,
        "arena_width": arena_size[0],
        "arena_height": arena_size[1],
        "homography": matrix.tolist(),
    }, indent=2), encoding="utf-8")
    temporary.replace(path)


def calibrate_camera_to_arena(
    camera: cv2.VideoCapture,
    arena_size: tuple[int, int],
    output_path: Path,
) -> np.ndarray:
    """Collect the arena's four corners in the overhead camera image."""
    points: list[tuple[int, int]] = []
    window_name = "mBot arena calibration"
    width, height = arena_size

    def on_mouse(event: int, x: int, y: int, _flags: int, _parameter: object) -> None:
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append((x, y))

    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, on_mouse)
    try:
        while len(points) < 4:
            ok, frame = camera.read()
            if not ok or frame is None:
                raise ArenaCalibrationError("Overhead camera stopped during calibration.")
            preview = frame.copy()
            labels = (
                "Click arena TOP-LEFT corner",
                "Click arena TOP-RIGHT corner",
                "Click arena BOTTOM-RIGHT corner",
                "Click arena BOTTOM-LEFT corner",
            )
            for index, point in enumerate(points):
                cv2.circle(preview, point, 8, (0, 255, 255), -1)
                cv2.putText(preview, str(index + 1), point, cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (0, 0, 0), 2)
            cv2.putText(preview, labels[len(points)], (15, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(preview, "Q cancels", (15, 58),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.imshow(window_name, preview)
            if cv2.waitKey(20) & 0xFF in (ord("q"), ord("Q"), 27):
                raise ArenaCalibrationError("Arena calibration cancelled.")
    finally:
        cv2.destroyWindow(window_name)

    image_points = np.asarray(points, dtype=np.float32)
    game_points = np.asarray(
        [(0, 0), (width, 0), (width, height), (0, height)],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(image_points, game_points)
    save_homography(output_path, matrix, arena_size)
    return matrix


class AprilTagTracker:
    def __init__(self, tag_id: int, homography: np.ndarray) -> None:
        if not hasattr(cv2, "aruco"):
            raise RuntimeError(
                "OpenCV AprilTag support is unavailable. Install opencv-contrib-python."
            )
        self.tag_id = tag_id
        self.homography = homography
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
        parameters = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(dictionary, parameters)

    def detect(self, frame: np.ndarray) -> tuple[Pose | None, np.ndarray | None]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _rejected = self.detector.detectMarkers(gray)
        if ids is None:
            return None, None
        for marker_corners, marker_id in zip(corners, ids.flatten()):
            if int(marker_id) != self.tag_id:
                continue
            image_corners = marker_corners.reshape(4, 2).astype(np.float32)
            center = image_corners.mean(axis=0)
            front_midpoint = (image_corners[0] + image_corners[1]) / 2
            points = np.asarray([center, front_midpoint], dtype=np.float32).reshape(-1, 1, 2)
            mapped = cv2.perspectiveTransform(points, self.homography).reshape(2, 2)
            direction = mapped[1] - mapped[0]
            if np.linalg.norm(direction) < 1e-6:
                return None, image_corners
            pose = Pose(
                float(mapped[0][0]),
                float(mapped[0][1]),
                float(np.arctan2(direction[1], direction[0])),
            )
            return pose, image_corners
        return None, None
