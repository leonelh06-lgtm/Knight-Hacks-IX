import unittest,time
from rover.vision import PoseSample,OverheadTracker
class VisionTests(unittest.TestCase):
 def test_snapshot_retains_capture_age(self):
  t=OverheadTracker(1,0,None);t._sample=PoseSample(None,10,False,'')
  self.assertEqual(t.latest().captured_at,10);self.assertFalse(t.latest().valid)
 def test_duplicate_tags_rejected(self):
  from rover.vision import unique_marker
  self.assertIsNone(unique_marker([1,2],[[0],[0]],0))
  self.assertIsNone(unique_marker([1],[[1]],0))
  self.assertEqual(unique_marker([7],[[0]],0),7)
