"""Camera-independent control logic. Coordinates use x-right and y-down."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Observation:
    x: float
    y: float
    opening: float
    pinches: tuple[float, float, float, float]
    heading: float = -math.pi / 2
    finger_openings: tuple[float, float, float, float] | None = None

    def valid(self):
        values = (self.x, self.y, self.opening, self.heading, *self.pinches)
        if self.finger_openings is not None:
            if len(self.finger_openings) != 4:
                return False
            values += self.finger_openings
        return len(self.pinches) == 4 and all(math.isfinite(v) for v in values)


@dataclass(frozen=True)
class Calibration:
    closed: float
    opened: float
    neutral_opening: float | None = None

    def __post_init__(self):
        if self.neutral_opening is None:
            object.__setattr__(self, 'neutral_opening', (self.closed + self.opened) / 2)
        values = (self.closed, self.opened, self.neutral_opening)
        if not all(math.isfinite(v) for v in values):
            raise ValueError('Calibration values must be finite.')
        if not 0 <= self.closed < self.opened <= 1 or self.opened - self.closed < 0.08:
            raise ValueError('Opening and relaxing were too similar. Retry within a comfortable range.')
        if not self.closed + .04 <= self.neutral_opening <= self.opened - .04:
            raise ValueError('Relaxed neutral must be between fist and open hand. Recalibrate with three distinct postures.')


@dataclass(frozen=True)
class Command:
    velocity: tuple[float, float]
    status: str
    active: bool = False


class Controller:
    def __init__(self, calibration=None, mode='movement', smoothing=0.3,
                 pinch_threshold=0.28):
        if mode not in ('movement', 'pinch'):
            raise ValueError('Unknown control mode.')
        if not 0 < smoothing <= 1 or pinch_threshold <= 0:
            raise ValueError('Invalid control sensitivity.')
        self.calibration = calibration
        self.mode = mode
        self.smoothing = smoothing
        self.pinch_threshold = pinch_threshold
        self._velocity = (0.0, 0.0)
        self._active = False
        self._direction = None

    def stop(self, reason='Paused'):
        self._velocity = (0.0, 0.0)
        self._active = False
        self._direction = None
        return Command(self._velocity, reason)

    def update(self, observation):
        if observation is None or not observation.valid():
            return self.stop('Hand not tracked')
        if self.calibration is None and self.mode == 'movement':
            return self.stop('Calibrate first: press C')
        if self.mode == 'pinch':
            index = min(range(4), key=lambda i: observation.pinches[i])
            if observation.pinches[index] >= self.pinch_threshold:
                return self.stop('Touch thumb to a finger to move')
            target = ((-1, 0), (0, -1), (1, 0), (0, 1))[index]
            status = ('Index: left', 'Middle: up', 'Ring: right', 'Little: down')[index]
            self._active = True
        else:
            cal = self.calibration
            low = (cal.closed + cal.neutral_opening) / 2
            high = (cal.opened + cal.neutral_opening) / 2
            fingers = observation.finger_openings or (observation.opening,) * 4
            # A fist naturally brings thumb and fingertips together. Check all
            # fingers before pinch distances to avoid interpreting it as steering.
            if observation.opening <= low and all(value <= low for value in fingers):
                direction, velocity, status = 'down', (0, 1), 'Closed fist: moving down'
            else:
                index_touch = observation.pinches[0] < self.pinch_threshold
                pinkie_touch = observation.pinches[3] < self.pinch_threshold
                if index_touch and pinkie_touch:
                    return self.stop('Both pinches detected: stopped')
                if index_touch or pinkie_touch:
                    pinching_finger = 0 if index_touch else 3
                    other_open = sum(value >= high for index, value in enumerate(fingers)
                                     if index != pinching_finger)
                    if other_open < 2:
                        return self.stop('Unclear pinch: keep other fingers open')
                    if index_touch:
                        direction, velocity, status = 'left', (-1, 0), 'Index-thumb pinch: moving left'
                    else:
                        direction, velocity, status = 'right', (1, 0), 'Pinkie-thumb pinch: moving right'
                elif observation.opening >= high and all(value >= high for value in fingers):
                    direction, velocity, status = 'up', (0, -1), 'Open hand: moving up'
                else:
                    return self.stop('Relaxed / unclear hand: stopped')
            self._direction = direction
            self._active = True
            self._velocity = velocity
            return Command(velocity, status, True)
        self._velocity = tuple(previous + self.smoothing * (next_value - previous)
                               for previous, next_value in zip(self._velocity, target))
        return Command(self._velocity, status, True)

def advance(position, velocity, speed, dt, bounds, radius):
    """Bound frame time and keep the whole character inside the arena."""
    dt = max(0, min(dt, 0.1))
    return tuple(max(radius, min(limit - radius, point + direction * speed * dt))
                 for point, direction, limit in zip(position, velocity, bounds))


def from_landmarks(points, aspect_ratio=1.0):
    """Estimate opening from finger bend angles; pinch distances use palm scale.

    These are image-derived gameplay features, not clinical joint measurements.
    Thumb opening is intentionally not required for the movement gate.
    """
    if len(points) != 21:
        raise ValueError('Expected 21 hand landmarks.')
    xyz = [(p.x, p.y, p.z) for p in points]
    if not all(math.isfinite(v) for point in xyz for v in point):
        raise ValueError('Invalid hand landmarks.')
    if not math.isfinite(aspect_ratio) or aspect_ratio <= 0:
        raise ValueError('Invalid camera aspect ratio.')
    # Image x/y are normalized independently. Convert y into width units so
    # camera geometry and diagonal headings are not distorted by aspect ratio.
    xyz = [(x, y * aspect_ratio, z) for x, y, z in xyz]
    def distance(a, b):
        return math.dist(xyz[a], xyz[b])
    scale = distance(0, 9)
    if scale < 1e-6:
        raise ValueError('Hand is too small or degenerate.')
    opening = []
    for mcp, pip, tip in ((5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20)):
        a = tuple(x - y for x, y in zip(xyz[mcp], xyz[pip]))
        b = tuple(x - y for x, y in zip(xyz[tip], xyz[pip]))
        denominator = math.hypot(*a) * math.hypot(*b)
        if denominator < 1e-9:
            raise ValueError('Degenerate finger landmarks.')
        cosine = sum(x * y for x, y in zip(a, b)) / denominator
        opening.append(math.acos(max(-1, min(1, cosine))) / math.pi)
    palm = (0, 5, 9, 13, 17)
    dx = sum(xyz[i][0] for i in (5, 9, 13, 17)) / 4 - xyz[0][0]
    dy = sum(xyz[i][1] for i in (5, 9, 13, 17)) / 4 - xyz[0][1]
    return Observation(sum(points[i].x for i in palm) / 5,
                       sum(points[i].y for i in palm) / 5,
                       sum(opening) / 4,
                       tuple(distance(4, tip) / scale for tip in (8, 12, 16, 20)),
                       math.atan2(dy, dx), tuple(opening))
