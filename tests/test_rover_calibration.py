import unittest,numpy as np
from rover.calibration import BoardCalibration
class CalibrationTests(unittest.TestCase):
 def cal(self):return BoardCalibration({'version':1,'calibration_id':'cal','camera':'1','image_size':[1280,720],'camera_matrix':[[1000,0,640],[0,1000,360],[0,0,1]],'distortion':[0,0,0,0,0],'rotation':np.eye(3).tolist(),'translation':[-457.2,-254,1000],'tag_height_mm':177.8,'centre_offset_mm':[0,0],'arena':{'x_mm':0,'y_mm':0,'width_mm':914.4,'height_mm':508},'validation_error_mm':None,'verified':False})
 def test_raised_tag_reconstructs_position(self):
  c=self.cal();world=np.array([[600,300,-177.8]])
  cam=world+np.array(c.data['translation']);pixels=cam[:,:2]/cam[:,2:]*1000+[640,360]
  np.testing.assert_allclose(c.image_to_board(pixels,177.8),[[600,300]],atol=1e-6)
  self.assertGreater(np.linalg.norm(c.image_to_board(pixels,0)-[[600,300]]),10)
 def test_heading_and_offset(self):
  c=self.cal();world=np.array([[550,280,-177.8],[570,280,-177.8],[570,300,-177.8],[550,300,-177.8]])
  cam=world+np.array(c.data['translation']);px=cam[:,:2]/cam[:,2:]*1000+[640,360]
  p=c.tag_to_rover(px,177.8,(10,0));self.assertAlmostEqual(p.x_mm,560);self.assertAlmostEqual(p.y_mm,280)
 def test_invalid_geometry_rejected(self):
  c=self.cal()
  with self.assertRaises(ValueError):c.image_to_board([[640,360]],1200)
  data=dict(c.data);data['rotation']=[[0,0,0]]*3
  with self.assertRaises(ValueError):BoardCalibration(data)
