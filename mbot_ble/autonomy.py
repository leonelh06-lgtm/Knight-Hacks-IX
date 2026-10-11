"""Geometry and pursuit decisions shared by the overhead-camera rover controller."""

from dataclasses import dataclass
import math


STOP = b"X"
FORWARD = b"W"
TURN_LEFT = b"A"
TURN_RIGHT = b"D"


@dataclass(frozen=True)
class Pose:
    x: float
    y: float
    heading: float


def wrap_angle(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


def pursuit_command(
    pose: Pose,
    target: tuple[float, float],
    arena_size: tuple[float, float],
    *,
    stop_distance: float = 32.0,
    heading_deadband: float = 0.30,
    boundary_margin: float = 42.0,
) -> bytes:
    """Choose a discrete motor command toward a clamped target in the arena."""
    values = (pose.x, pose.y, pose.heading, *target, *arena_size,
              stop_distance, heading_deadband, boundary_margin)
    if not all(math.isfinite(value) for value in values):
        return STOP
    width, height = arena_size
    if width <= 0 or height <= 0 or boundary_margin <= 0:
        return STOP
    if boundary_margin * 2 >= min(width, height):
        return STOP
    if not (0 <= pose.x <= width and 0 <= pose.y <= height):
        return STOP

    safe_x = min(width - boundary_margin, max(boundary_margin, target[0]))
    safe_y = min(height - boundary_margin, max(boundary_margin, target[1]))
    at_boundary = (
        pose.x < boundary_margin
        or pose.x > width - boundary_margin
        or pose.y < boundary_margin
        or pose.y > height - boundary_margin
    )
    if at_boundary:
        safe_x, safe_y = width / 2, height / 2

    dx, dy = safe_x - pose.x, safe_y - pose.y
    distance = math.hypot(dx, dy)
    if distance <= stop_distance:
        return STOP

    desired_heading = math.atan2(dy, dx)
    error = wrap_angle(desired_heading - pose.heading)
    if error > heading_deadband:
        return TURN_RIGHT
    if error < -heading_deadband:
        return TURN_LEFT
    return FORWARD
