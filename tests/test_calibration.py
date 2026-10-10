import unittest
import math
from gesture_control.calibration import build_calibration, Wizard, CalibrationError
from gesture_control.controls import Observation


class CalibrationTests(unittest.TestCase):
    def test_builds_personal_up_direction_and_opening(self):
        neutral = [Observation(.5, .5, .5, (1, 1, 1, 1))] * 20
        relaxed = [Observation(.5, .5, .3, (1, 1, 1, 1))] * 20
        opened = [Observation(.5, .5, .8, (1, 1, 1, 1))] * 20
        left = [Observation(.5, .5, .5, (1, 1, 1, 1), -math.pi / 2 - .4)] * 20
        right = [Observation(.5, .5, .5, (1, 1, 1, 1), -math.pi / 2 + .3)] * 20
        cal = build_calibration([neutral, relaxed, opened, left, right])
        self.assertAlmostEqual(cal.heading_offset, 0)
        self.assertEqual(cal.closed, .3)
        self.assertEqual(cal.neutral_opening, .5)
        self.assertAlmostEqual(cal.left_range, .4)
        self.assertAlmostEqual(cal.right_range, .3)

    def test_insufficient_tracking_samples_are_rejected(self):
        with self.assertRaises(ValueError):
            build_calibration([[], [], [], [], []])

    def test_bad_neutral_identifies_only_neutral_step(self):
        def group(opening, heading=-math.pi / 2):
            return [Observation(.5, .5, opening, (1, 1, 1, 1), heading)] * 20
        groups = [group(.8), group(.3), group(.8), group(.5, -math.pi / 2 - .4),
                  group(.5, -math.pi / 2 + .3)]
        with self.assertRaises(CalibrationError) as raised:
            build_calibration(groups)
        self.assertEqual(raised.exception.step, 0)

    def test_retry_keeps_good_recordings_and_finishes_after_one_replacement(self):
        wizard = Wizard()
        sample = Observation(.5, .5, .5, (1, 1, 1, 1))
        wizard.groups = [[sample] * 20 for _ in range(5)]
        preserved = wizard.groups[0]
        wizard.retry_step(4)
        self.assertIs(wizard.groups[0], preserved)
        self.assertEqual(wizard.step, 4)
        wizard.start_step(10)
        for index in range(20):
            wizard.update(11 + index * .1, sample, True)
        self.assertTrue(wizard.update(14, sample, False))
        self.assertIs(wizard.groups[0], preserved)

    def test_slow_tracking_gets_more_time_instead_of_immediate_retry(self):
        wizard = Wizard()
        wizard.start_step(0)
        sample = Observation(.5, .5, .5, (1, 1, 1, 1))
        for second in range(1, 5):
            self.assertFalse(wizard.update(second, sample, True))
        self.assertEqual(wizard.step, 0)
        self.assertEqual(wizard.started, 0)

    def test_missing_tracking_eventually_requires_explicit_retry(self):
        wizard = Wizard()
        wizard.start_step(0)
        with self.assertRaises(CalibrationError) as raised:
            wizard.update(12, None, True)
        self.assertEqual(raised.exception.step, 0)
        self.assertIsNone(wizard.started)
