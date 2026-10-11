import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import test_rover_calibration as calibration_tests
from test_rover_pursuit import config
from rover.__main__ import load_setup
from rover.calibration_tools import validate_calibration
from rover.types import Pose
class Tests(unittest.TestCase):
 def test_loader_accepts_verified_calibration_without_fixed_tags(self):
  c=calibration_tests.CalibrationTests().cal()
  c.data.update(verified=True,validation_error_mm=5,projection_size=[1280,720])
  with patch('rover.__main__.read_config',return_value=config()),patch('rover.__main__.BoardCalibration.load',return_value=c):
   cfg,_=load_setup(SimpleNamespace(config='cfg',calibration='cal',camera=1,tag_id=0))
  self.assertTrue(cfg['calibration_verified']);self.assertNotIn('guard_error_mm',cfg)
 def test_reference_validation_requires_only_rover_tag(self):
  points=[(200,150),(700,150),(200,350),(700,350),(457,254)]
  poses=iter(points+[points[-1]])
  saved=[]
  c=SimpleNamespace(data=dict(camera='1',image_size=[1280,720],tag_height_mm=177.8,centre_offset_mm=[0,0],camera_guard={'old':'unused'}),
       tag_to_rover=lambda *a:Pose(*next(poses),0),save=lambda path:saved.append(dict(c.data)))
  class Capture:
   def read(self):return True,np.zeros((720,1280,3),np.uint8)
   def release(self):pass
  class Detector:
   def detectMarkers(self,frame):return [np.zeros((1,4,2),float)],np.array([[0]]),[]
  with patch('rover.calibration_tools.BoardCalibration.load',return_value=c),patch('rover.calibration_tools.open_camera',return_value=Capture()),patch('cv2.aruco.ArucoDetector',return_value=Detector()),patch('cv2.imshow'),patch('cv2.destroyAllWindows'),patch('cv2.waitKey',side_effect=[32]*5+[13]),patch('builtins.input',side_effect=[f'{x} {y}' for x,y in points]):
   validate_calibration(1,'auto','cal',0)
  self.assertEqual(len(saved),1);self.assertTrue(saved[0]['verified']);self.assertNotIn('camera_guard',saved[0]);self.assertEqual(saved[0]['validation_error_mm'],0)
