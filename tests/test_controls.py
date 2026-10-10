import math
import unittest

from gesture_control.controls import Calibration, Controller, Observation, advance, from_landmarks
from types import SimpleNamespace


def hand(x=0.5, y=0.5, opening=0.9, pinches=(1, 1, 1, 1), heading=-math.pi / 2):
    return Observation(x, y, opening, pinches, heading)


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.cal = Calibration(0, 0.2, 0.8)
        self.control = Controller(self.cal, smoothing=1)

    def test_requires_calibration_before_moving(self):
        self.assertEqual(Controller().update(hand(x=0.9)).velocity, (0, 0))

    def test_open_hand_steers_right(self):
        command = self.control.update(hand(heading=0))
        self.assertAlmostEqual(command.velocity[0], 1)
        self.assertEqual(command.velocity[1], 0)

    def test_fist_at_neutral_moves_down(self):
        self.assertEqual(self.control.update(hand(opening=.2)).velocity, (0, 1))

    def test_relaxed_neutral_stops_without_smoothing_tail(self):
        control = Controller(self.cal, smoothing=.3)
        control.update(hand())
        self.assertEqual(control.update(hand(opening=.5)).velocity, (0, 0))

    def test_tilt_overrides_fist_and_opening(self):
        for opening in (.2, .5, .9):
            self.assertEqual(self.control.update(hand(opening=opening, heading=-math.pi / 2 - .5)).velocity, (-1, 0))
            self.assertEqual(self.control.update(hand(opening=opening, heading=-math.pi / 2 + .5)).velocity, (1, 0))

    def test_missing_hand_stops_immediately(self):
        self.control.update(hand(x=0.7))
        self.assertEqual(self.control.update(None).velocity, (0, 0))

    def test_open_hand_at_center_keeps_moving_up(self):
        vx, vy = self.control.update(hand()).velocity
        self.assertAlmostEqual(vx, 0)
        self.assertAlmostEqual(vy, -1)

    def test_translation_does_not_change_steering(self):
        first = self.control.update(hand(x=.2, y=.3, heading=.5)).velocity
        second = self.control.update(hand(x=.8, y=.9, heading=.5)).velocity
        self.assertEqual(first, second)

    def test_calibrated_up_compensates_for_camera_rotation(self):
        control = Controller(Calibration(-math.pi / 2, .2, .8), smoothing=1)
        vx, vy = control.update(hand(heading=0)).velocity
        self.assertAlmostEqual(vx, 0)
        self.assertAlmostEqual(vy, -1)

    def test_diagonal_tilt_selects_right_instead_of_up(self):
        x, y = self.control.update(hand(heading=-math.pi / 4)).velocity
        self.assertAlmostEqual(math.hypot(x, y), 1)
        self.assertGreater(x, 0)
        self.assertEqual(y, 0)

    def test_pinch_directions_and_release(self):
        control = Controller(self.cal, mode='pinch', smoothing=1)
        for index, expected in enumerate(((-1, 0), (0, -1), (1, 0), (0, 1))):
            pinches = [1, 1, 1, 1]
            pinches[index] = 0.1
            self.assertEqual(control.update(hand(pinches=tuple(pinches))).velocity, expected)
        self.assertEqual(control.update(hand()).velocity, (0, 0))

    def test_invalid_calibration_is_rejected(self):
        with self.assertRaises(ValueError):
            Calibration(0, 0.8, 0.2)

    def test_pinch_mode_works_without_opening_calibration(self):
        control = Controller(mode='pinch', smoothing=1)
        self.assertEqual(control.update(hand(pinches=(.1, 1, 1, 1))).velocity, (-1, 0))

    def test_invalid_landmark_values_stop(self):
        self.assertEqual(self.control.update(hand(x=float('nan'))).velocity, (0, 0))

    def test_character_stays_inside_map(self):
        self.assertEqual(advance((95, 5), (1, -1), 100, 1, (100, 100), 10), (90, 10))

    def test_frame_delay_does_not_cause_large_jump(self):
        self.assertEqual(advance((50, 50), (1, 0), 100, 10, (1000, 1000), 10), (60, 50))

    def test_top_down_landmarks_use_wrist_to_knuckles_heading(self):
        points = [SimpleNamespace(x=.55, y=.8, z=0) for _ in range(21)]
        for x, indices in zip((.4, .5, .6, .7), ((5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20))):
            for y, index in zip((.6, .45, .3), indices):
                points[index] = SimpleNamespace(x=x, y=y, z=0)
        result = from_landmarks(points, aspect_ratio=.75)
        self.assertAlmostEqual(result.heading, -math.pi / 2)
        self.assertAlmostEqual(result.opening, 1)

    def test_small_tilt_keeps_open_hand_moving_up(self):
        self.assertEqual(self.control.update(hand(heading=-math.pi / 2 + .05)).velocity, (0, -1))

    def test_personal_tilt_range_works_for_small_movements(self):
        control = Controller(Calibration(0, .2, .8, .5, .2, .2), smoothing=1)
        self.assertEqual(control.update(hand(heading=-math.pi / 2 + .15)).velocity, (1, 0))

    def test_turning_across_angle_wrap_keeps_calibrated_up(self):
        control = Controller(Calibration(-math.pi / 2 - math.pi, .2, .8), smoothing=.3)
        control.update(hand(heading=math.radians(179)))
        vx, vy = control.update(hand(heading=math.radians(-179))).velocity
        self.assertEqual((vx, vy), (0, -1))


if __name__ == '__main__':
    unittest.main()
