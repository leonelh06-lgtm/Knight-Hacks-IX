import unittest
import importlib.util
from unittest.mock import patch
from gesture_control.tracking import Tracker, Snapshot


class StartupTests(unittest.TestCase):
    def test_invalid_inference_device_is_rejected(self):
        with self.assertRaises(ValueError):
            Tracker('unused.task', inference_device='invalid')

    @unittest.skipUnless(importlib.util.find_spec('mediapipe'), 'MediaPipe not installed')
    def test_gpu_failure_does_not_retry_on_cpu(self):
        from mediapipe.tasks.python import vision
        from gesture_control.tracking import create_detector
        with patch.object(vision.HandLandmarker, 'create_from_options', side_effect=RuntimeError('GPU unavailable')) as factory:
            with self.assertRaisesRegex(RuntimeError, 'GPU.*no CPU fallback'):
                create_detector('unused.task', 'any', 'gpu')
            self.assertEqual(factory.call_count, 1)
            import mediapipe as mp
            self.assertEqual(factory.call_args.args[0].base_options.delegate, mp.tasks.BaseOptions.Delegate.GPU)

    def test_stuck_camera_startup_reports_timeout(self):
        tracker = Tracker('unused.task', startup_timeout=5)
        tracker.started_at = 10
        snapshot = tracker.latest(now=16)
        self.assertIn('Opening camera', snapshot.error)
        self.assertIn('--camera-backend dshow', snapshot.error)

    def test_running_tracker_does_not_trigger_startup_timeout(self):
        tracker = Tracker('unused.task', startup_timeout=5)
        tracker.started_at = 10
        tracker._publish(Snapshot(timestamp=15, phase='Tracking'))
        self.assertEqual(tracker.latest(now=20).error, '')
