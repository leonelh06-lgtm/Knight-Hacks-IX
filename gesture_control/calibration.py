"""Personal top-down direction and opening calibration."""

from statistics import median
import math
from .controls import Calibration

STEPS = (
    'Point straight ahead with fingers partly relaxed: this is STOP',
    'Close your fingers into a comfortable fist (do not force it)',
    'Open your fingers as far as comfortably possible',
    'Tilt your hand comfortably LEFT; hold that angle',
    'Tilt your hand comfortably RIGHT; hold that angle',
)

MIN_SAMPLES = 15
RECORDING_SECONDS = 4
MAX_RECORDING_SECONDS = 12


class CalibrationError(ValueError):
    def __init__(self, step, message):
        super().__init__(message)
        self.step = step


def build_calibration(groups):
    if len(groups) != len(STEPS):
        raise CalibrationError(0, 'Calibration requires all five poses.')
    for index, group in enumerate(groups):
        if len(group) < MIN_SAMPLES:
            raise CalibrationError(index, 'Too few tracked samples. Keep the entire hand visible and retry this step.')
        if any(not sample.valid() for sample in group):
            raise CalibrationError(index, 'Invalid tracking samples. Retry this step with the hand clearly visible.')
    neutral, relaxed, opened, left, right = groups
    cosine = sum(math.cos(sample.heading) for sample in neutral) / len(neutral)
    sine = sum(math.sin(sample.heading) for sample in neutral) / len(neutral)
    if math.hypot(cosine, sine) < .9:
        raise CalibrationError(0, 'Neutral direction was not steady. Hold the wrist still, pointing straight ahead.')
    neutral_heading = math.atan2(sine, cosine)
    def tilt_range(samples, sign):
        angles = [math.atan2(math.sin(sample.heading - neutral_heading),
                            math.cos(sample.heading - neutral_heading)) for sample in samples]
        return sign * median(angles)
    closed_value = median(sample.opening for sample in relaxed)
    opened_value = median(sample.opening for sample in opened)
    neutral_value = median(sample.opening for sample in neutral)
    if not 0 <= closed_value < opened_value <= 1 or opened_value - closed_value < .08:
        raise CalibrationError(2, f'Open and fist poses are too similar (fist {closed_value:.2f}, open {opened_value:.2f}). '
                               'Record a visibly open hand; press C only if you need to redo the fist too.')
    if not closed_value + .04 <= neutral_value <= opened_value - .04:
        raise CalibrationError(0, f'Neutral fingers must be partly relaxed, between fist and open '
                               f'(neutral {neutral_value:.2f}, fist {closed_value:.2f}, open {opened_value:.2f}).')
    left_value, right_value = tilt_range(left, -1), tilt_range(right, 1)
    for index, value, name in ((3, left_value, 'LEFT'), (4, right_value, 'RIGHT')):
        if not math.radians(8) <= value <= math.pi / 2:
            raise CalibrationError(index, f'{name} tilt measured {math.degrees(value):.0f} degrees. '
                                   f'Hold a comfortable {name.lower()} angle 8-90 degrees from neutral.')
    return Calibration(-math.pi / 2 - neutral_heading, closed_value, opened_value,
                       neutral_value, left_value, right_value)


class Wizard:
    def __init__(self):
        self.groups = [[] for _ in STEPS]
        self.step = 0
        self.started = None

    def start_step(self, now):
        self.groups[self.step] = []
        self.started = now

    def retry_step(self, step):
        """Replace only the failed pose; preserve other completed recordings."""
        self.step = step
        self.groups[step] = []
        self.started = None

    def update(self, now, observation, fresh):
        if self.started is None:
            return False
        elapsed = now - self.started
        # One second of preparation followed by three seconds of recording.
        if elapsed >= 1 and fresh and observation is not None:
            self.groups[self.step].append(observation)
        if elapsed < RECORDING_SECONDS:
            return False
        if len(self.groups[self.step]) < MIN_SAMPLES and elapsed < MAX_RECORDING_SECONDS:
            return False
        self.started = None
        if len(self.groups[self.step]) < MIN_SAMPLES:
            raise CalibrationError(self.step, f'Only {len(self.groups[self.step])}/{MIN_SAMPLES} tracked samples in '
                                   f'{MAX_RECORDING_SECONDS}s. Check camera view and frame age; Enter retries this step.')
        self.step = next((index for index, group in enumerate(self.groups) if len(group) < MIN_SAMPLES), len(STEPS))
        return self.step == len(STEPS)
