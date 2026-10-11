import unittest,time,threading
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from rover.vision import PoseSample,OverheadTracker
from rover.types import Pose
from rover.calibration import BoardCalibration
class Capture:
 def __init__(self):self.closed=False
 def set(self,*a):pass
 def read(self):return True,np.zeros((20,30,3),np.uint8)
 def release(self):self.closed=True
class VisionTests(unittest.TestCase):
 def cal(self):
  return BoardCalibration(dict(version=1,calibration_id='c',camera='1',image_size=[30,20],tag_height_mm=10,centre_offset_mm=[0,0],camera_matrix=[[20,0,15],[0,20,10],[0,0,1]],distortion=[0]*5,rotation=np.eye(3).tolist(),translation=[-457.2,-254,1000],arena=dict(x_mm=0,y_mm=0,width_mm=914.4,height_mm=508)))
 def test_snapshot_retains_capture_age(self):
  t=OverheadTracker(1,0,None);t._sample=PoseSample(None,10,False,'')
  self.assertEqual(t.latest().captured_at,10);self.assertFalse(t.latest().valid)
 def test_duplicate_tags_rejected(self):
  from rover.vision import unique_marker
  self.assertIsNone(unique_marker([1,2],[[0],[0]],0));self.assertIsNone(unique_marker([1],[[1]],0));self.assertEqual(unique_marker([7],[[0]],0),7)
 def test_stalled_detector_does_not_refresh_capture(self):
  entered=threading.Event();release=threading.Event();cap=Capture();marker=np.array([[[10,10],[15,10],[15,15],[10,15]]],float);guard=np.array([[[1,1],[5,1],[5,5],[1,5]]],float)
  class Detector:
   def detectMarkers(self,frame):
    entered.set();release.wait(2);return [marker],np.array([[0]]),[]
  with patch('rover.vision.open_camera',return_value=cap),patch('cv2.aruco.ArucoDetector',return_value=Detector()):
   t=OverheadTracker(1,0,self.cal());start=time.monotonic();t.start();self.assertTrue(entered.wait(1))
   self.assertFalse(t.latest().valid);self.assertLess(time.monotonic()-start,1);time.sleep(.08);t._stop.set();release.set();t.close()
   self.assertTrue(t.latest().valid);self.assertLess(t.latest().captured_at-start,.05);self.assertTrue(cap.closed)
 def test_single_rover_tag_tracks_without_reference_tags(self):
  cap=Capture()
  class Detector:
   def detectMarkers(self,frame):
    return [np.array([[[10,10],[15,10],[15,15],[10,15]]],float)],np.array([[0]]),[]
  with patch('rover.vision.open_camera',return_value=cap),patch('cv2.aruco.ArucoDetector',return_value=Detector()):
   t=OverheadTracker(1,0,self.cal());t.start()
   deadline=time.monotonic()+1
   while not t.latest().valid and not t.latest().error and time.monotonic()<deadline:time.sleep(.005)
   t.close();self.assertTrue(t.latest().valid,t.latest().error);self.assertTrue(cap.closed)
 def test_failed_read_invalid(self):
  cap=Capture();cap.read=lambda:(False,None)
  with patch('rover.vision.open_camera',return_value=cap):
   t=OverheadTracker(1,0,self.cal());t.start();t._thread.join(1);self.assertFalse(t.latest().valid);self.assertTrue(t.latest().error);self.assertTrue(cap.closed)
