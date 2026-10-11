import unittest,math
import numpy as np,cv2
import test_rover_calibration as calibration_tests
from rover.camera_guard import CameraGuard,MAX_CAMERA_DRIFT_MM
class Tests(unittest.TestCase):
 def setup(self):
  c=calibration_tests.CalibrationTests().cal()
  def pixels(world,R=None):
   R=c.R if R is None else R
   return cv2.projectPoints(np.asarray(world,float),cv2.Rodrigues(R)[0],c.t,c.K,c.D)[0].reshape(-1,2)
  refs=[np.array([[-50,-30,0],[-10,-30,0],[-10,10,0],[-50,10,0]]),np.array([[925,510,0],[965,510,0],[965,550,0],[925,550,0]])]
  c.data['camera_guard']={'markers':[dict(tag_id=i+1,corners_px=pixels(w).tolist()) for i,w in enumerate(refs)]}
  return c,refs,pixels
 def test_camera_roll_that_small_local_tag_would_miss(self):
  c,refs,pixels=self.setup();guard=CameraGuard(c);a=math.radians(4);R=np.array([[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1.]])
  # Rotate about optical axis rather than world origin.
  changed_t=R@c.t
  moved=[cv2.projectPoints(w.astype(float),cv2.Rodrigues(R)[0],changed_t,c.K,c.D)[0] for w in refs]
  with self.assertRaisesRegex(ValueError,'moved'):guard.check(moved,np.array([[1],[2]]))
 def test_stationary_references_and_missing_guard(self):
  c,refs,pixels=self.setup();guard=CameraGuard(c)
  self.assertTrue(guard.check([pixels(w) for w in refs],np.array([[1],[2]])))
  self.assertFalse(guard.check([pixels(refs[0])],np.array([[1]])))
  self.assertEqual(MAX_CAMERA_DRIFT_MM,4)
 def test_small_local_guard_cannot_arm(self):
  c,refs,pixels=self.setup();c.data['camera_guard']['markers'][1]['corners_px']=pixels(refs[0]+[50,50,0]).tolist()
  with self.assertRaisesRegex(ValueError,'span'):CameraGuard(c)
 def test_raised_plane_error_is_checked(self):
  c,refs,pixels=self.setup();guard=CameraGuard(c)
  moved=[cv2.projectPoints(w.astype(float),cv2.Rodrigues(c.R)[0],c.t+np.array([0,0,-30]),c.K,c.D)[0] for w in refs]
  with self.assertRaisesRegex(ValueError,'moved'):guard.check(moved,np.array([[1],[2]]))
if __name__=='__main__':unittest.main()
