"""Personal palm-facing opening calibration."""

from statistics import median
from .controls import Calibration

STEPS = (
    'Face your palm toward the camera with fingers partly relaxed: STOP',
    'Close your fingers into a comfortable fist (do not force it)',
    'Open your fingers as far as comfortably possible',
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
        raise CalibrationError(0, 'Calibration requires all three poses.')
    for index, group in enumerate(groups):
        if len(group) < MIN_SAMPLES:
            raise CalibrationError(index, 'Too few tracked samples. Keep the entire hand visible and retry this step.')
        if any(not sample.valid() for sample in group):
            raise CalibrationError(index, 'Invalid tracking samples. Retry this step with the hand clearly visible.')
    neutral, relaxed, opened = groups
    closed_value = median(sample.opening for sample in relaxed)
    opened_value = median(sample.opening for sample in opened)
    neutral_value = median(sample.opening for sample in neutral)
    if not 0 <= closed_value < opened_value <= 1 or opened_value - closed_value < .08:
        raise CalibrationError(2, f'Open and fist poses are too similar (fist {closed_value:.2f}, open {opened_value:.2f}). '
                               'Record a visibly open hand; press C only if you need to redo the fist too.')
    if not closed_value + .04 <= neutral_value <= opened_value - .04:
        raise CalibrationError(0, f'Neutral fingers must be partly relaxed, between fist and open '
                               f'(neutral {neutral_value:.2f}, fist {closed_value:.2f}, open {opened_value:.2f}).')
    return Calibration(closed_value, opened_value, neutral_value)


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
