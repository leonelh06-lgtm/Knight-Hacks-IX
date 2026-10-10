import unittest
from gesture_control.tracking import Tracker, Snapshot


class StartupTests(unittest.TestCase):
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
