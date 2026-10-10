import unittest
from dataclasses import replace
import threading
import time
from unittest.mock import patch

from gesture_control.controls import advance
from gesture_control.tracking import Snapshot
from gesture_control.smolvlm import gesture_command, SmolTracker


class SmolControlTests(unittest.TestCase):
    def test_predictions_move_player_in_all_four_directions(self):
        for label, velocity in [('open_palm', (0, -1)), ('fist', (0, 1)),
                                ('index_pinch', (-1, 0)), ('pinkie_pinch', (1, 0))]:
            with self.subTest(label=label):
                snapshot = Snapshot(timestamp=10, prediction_timestamp=9.5, prediction=label)
                command = gesture_command(snapshot, 10.1, 2, .35)
                self.assertTrue(command.active)
                self.assertEqual(command.velocity, velocity)
                self.assertEqual(advance((100, 100), velocity, 100, .1, (500, 500), 15),
                                 (100 + velocity[0] * 10, 100 + velocity[1] * 10))

    def test_fresh_preview_does_not_refresh_old_prediction(self):
        snapshot = Snapshot(timestamp=20, prediction_timestamp=10, prediction='fist')
        self.assertFalse(gesture_command(snapshot, 20.1, 2, .35).active)

    def test_recent_prediction_cannot_move_with_stalled_camera(self):
        snapshot = Snapshot(timestamp=10, prediction_timestamp=11, prediction='fist')
        self.assertFalse(gesture_command(snapshot, 11.1, 2, .35).active)

    def test_unknown_error_and_missing_prediction_stop(self):
        snapshot = Snapshot(timestamp=10, prediction_timestamp=10, prediction='unknown')
        for change in ({}, {'prediction': 'Maybe fist'}, {'prediction_timestamp': 0},
                       {'prediction': 'fist', 'error': 'Camera failed'}):
            self.assertFalse(gesture_command(replace(snapshot, **change), 10.1, 2, .35).active)

    def test_future_capture_timestamp_cannot_move(self):
        snapshot = Snapshot(timestamp=12, prediction_timestamp=12, prediction='fist')
        self.assertFalse(gesture_command(snapshot, 10, 2, .35).active)

    def test_model_startup_timeout_is_reported(self):
        tracker = SmolTracker(startup_timeout=5)
        tracker.started_at = 10
        self.assertIn('timed out', tracker.latest(now=16).error)

    def test_loading_failure_is_reported_without_fallback(self):
        tracker = SmolTracker()
        tracker._frame_ready.set()
        with patch('gesture_control.smolvlm.LocalModel', side_effect=RuntimeError('CUDA unavailable')) as factory:
            tracker._infer()
        self.assertEqual(factory.call_count, 1)
        self.assertIn('CUDA unavailable', tracker.latest().error)
        self.assertIn('No CPU fallback', tracker.latest().error)

    def test_preview_keeps_updating_during_slow_inference(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest('NumPy not installed')
        entered, release = threading.Event(), threading.Event()
        tracker = SmolTracker()
        class Camera:
            def set(self, *args):
                pass
            def read(self):
                time.sleep(.01)
                return True, np.zeros((10, 10, 3), dtype=np.uint8)
            def release(self):
                pass
        class SlowModel:
            def __init__(self, *args):
                pass
            def predict(self, rgb):
                entered.set()
                release.wait(2)
                return 'fist', 100
        with patch('gesture_control.smolvlm.open_camera', return_value=Camera()), \
             patch('gesture_control.smolvlm.LocalModel', SlowModel):
            tracker.start()
            try:
                self.assertTrue(entered.wait(2))
                first = tracker.latest().timestamp
                deadline = time.monotonic() + 1
                while tracker.latest().timestamp <= first and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertGreater(tracker.latest().timestamp, first)
                self.assertEqual(tracker.latest().prediction_timestamp, 0)
            finally:
                release.set()
                tracker.close()


if __name__ == '__main__':
    unittest.main()
