import math
import unittest
from types import SimpleNamespace
from gesture_control.controls import Calibration, Controller, Observation, advance, from_landmarks


def hand(opening=.9, pinches=(1, 1, 1, 1), fingers=None, x=.5, y=.5, heading=-math.pi / 2):
    return Observation(x, y, opening, pinches, heading, fingers)


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.cal = Calibration(.2, .8, .5)
        self.control = Controller(self.cal, smoothing=1)

    def test_requires_calibration(self):
        self.assertEqual(Controller().update(hand()).velocity, (0, 0))

    def test_open_palm_moves_up(self):
        self.assertEqual(self.control.update(hand()).velocity, (0, -1))

    def test_fist_moves_down_even_when_thumb_is_near_fingers(self):
        self.assertEqual(self.control.update(hand(.2, (.1, .1, .1, .1))).velocity, (0, 1))

    def test_index_pinch_moves_left(self):
        self.assertEqual(self.control.update(hand(.75, (.1, 1, 1, 1), (.3, .9, .9, .9))).velocity, (-1, 0))

    def test_pinkie_pinch_moves_right(self):
        self.assertEqual(self.control.update(hand(.75, (1, 1, 1, .1), (.9, .9, .9, .3))).velocity, (1, 0))

    def test_both_pinches_stop(self):
        self.assertEqual(self.control.update(hand(.6, (.1, 1, 1, .1), (.3, .9, .9, .3))).velocity, (0, 0))

    def test_pinch_with_other_fingers_curled_stops(self):
        self.assertEqual(self.control.update(hand(.4, (.1, 1, 1, 1), (.3, .3, .9, .3))).velocity, (0, 0))

    def test_relaxed_hand_stops_immediately(self):
        control = Controller(self.cal, smoothing=.3)
        control.update(hand())
        self.assertEqual(control.update(hand(.5)).velocity, (0, 0))

    def test_tracking_loss_stops_immediately(self):
        self.control.update(hand())
        self.assertEqual(self.control.update(None).velocity, (0, 0))

    def test_rotation_and_translation_do_not_steer(self):
        for angle in (-math.pi, 0, math.pi / 2):
            self.assertEqual(self.control.update(hand(x=.1, y=.8, heading=angle)).velocity, (0, -1))

    def test_invalid_landmarks_stop(self):
        self.assertEqual(self.control.update(hand(opening=float('nan'))).velocity, (0, 0))

    def test_pinch_mode_directions_remain_available(self):
        control = Controller(mode='pinch', smoothing=1)
        for index, expected in enumerate(((-1, 0), (0, -1), (1, 0), (0, 1))):
            pinches = [1, 1, 1, 1]
            pinches[index] = .1
            self.assertEqual(control.update(hand(pinches=tuple(pinches))).velocity, expected)
        self.assertEqual(control.update(hand()).velocity, (0, 0))

    def test_invalid_calibration_rejected(self):
        with self.assertRaises(ValueError):
            Calibration(.8, .2, .5)

    def test_character_stays_inside_map(self):
        self.assertEqual(advance((95, 5), (1, -1), 100, 1, (100, 100), 10), (90, 10))

    def test_frame_delay_does_not_cause_large_jump(self):
        self.assertEqual(advance((50, 50), (1, 0), 100, 10, (1000, 1000), 10), (60, 50))

    def test_landmarks_preserve_individual_finger_opening(self):
        points = [SimpleNamespace(x=.55, y=.8, z=0) for _ in range(21)]
        for x, indices in zip((.4, .5, .6, .7), ((5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20))):
            for y, index in zip((.6, .45, .3), indices):
                points[index] = SimpleNamespace(x=x, y=y, z=0)
        result = from_landmarks(points, aspect_ratio=.75)
        self.assertEqual(result.finger_openings, (1, 1, 1, 1))
