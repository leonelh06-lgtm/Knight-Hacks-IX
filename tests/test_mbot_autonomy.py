import math
import unittest

from mbot_ble.autonomy import (
    FORWARD,
    STOP,
    TURN_LEFT,
    TURN_RIGHT,
    Pose,
    pursuit_command,
    wrap_angle,
)


class PursuitCommandTests(unittest.TestCase):
    arena = (750.0, 620.0)

    def test_forward_when_target_is_ahead(self):
        self.assertEqual(
            pursuit_command(Pose(100, 100, 0), (200, 100), self.arena),
            FORWARD,
        )

    def test_turns_right_and_left_to_align(self):
        self.assertEqual(
            pursuit_command(Pose(100, 100, 0), (100, 200), self.arena),
            TURN_RIGHT,
        )
        self.assertEqual(
            pursuit_command(Pose(100, 100, 0), (100, 0), self.arena),
            TURN_LEFT,
        )

    def test_stops_at_target(self):
        self.assertEqual(
            pursuit_command(Pose(100, 100, 0), (120, 100), self.arena),
            STOP,
        )

    def test_outside_arena_stops(self):
        self.assertEqual(
            pursuit_command(Pose(-1, 100, 0), (200, 100), self.arena),
            STOP,
        )

    def test_near_boundary_reorients_toward_center(self):
        self.assertEqual(
            pursuit_command(Pose(20, 310, math.pi), (200, 310), self.arena),
            TURN_LEFT,
        )

    def test_non_finite_input_stops(self):
        self.assertEqual(
            pursuit_command(Pose(math.nan, 100, 0), (200, 100), self.arena),
            STOP,
        )

    def test_wrap_angle(self):
        self.assertAlmostEqual(wrap_angle(3 * math.pi), -math.pi)


if __name__ == "__main__":
    unittest.main()
