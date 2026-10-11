import unittest
from rover.__main__ import diagnostic_line
from rover.pursuit import Decision
from rover.types import Pose,PoseSample
class Tests(unittest.TestCase):
 def test_pose_and_source_age_visible_while_unverified(self):
  line=diagnostic_line(PoseSample(Pose(300,200,1.57),10,True),Decision(b'X',False,'measurements unverified'),10.1)
  for value in ('300.0','200.0','90.0','100ms','VALID','unverified','X'):self.assertIn(value,line)
 def test_stale_label_and_missing_pose(self):
  self.assertIn('STALE',diagnostic_line(PoseSample(Pose(300,200,0),10,True),Decision(b'X',False,'stopped'),11))
  self.assertIn('INVALID',diagnostic_line(PoseSample(None,0,False),Decision(b'X',False,'stopped'),11))
