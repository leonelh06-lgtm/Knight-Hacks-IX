"""Calibrated viewing rays intersect the raised marker plane, not the tabletop."""
import json,math
from pathlib import Path
import numpy as np
import cv2
from .types import Pose
class BoardCalibration:
 def __init__(self,data):
  self.data=data
  if data.get('version')!=1 or not isinstance(data.get('calibration_id'),str) or not data['calibration_id']:raise ValueError('Calibration identity missing')
  self.K=np.asarray(data['camera_matrix'],float);self.D=np.asarray(data['distortion'],float);self.R=np.asarray(data['rotation'],float);self.t=np.asarray(data['translation'],float).reshape(3)
  if self.K.shape!=(3,3) or self.R.shape!=(3,3) or self.D.size not in (4,5,8,12,14):raise ValueError('Invalid camera geometry')
  if not all(np.isfinite(a).all() for a in (self.K,self.D,self.R,self.t)):raise ValueError('Nonfinite geometry')
  if self.K[0,0]<=0 or self.K[1,1]<=0 or abs(np.linalg.det(self.K))<1e-9 or not np.allclose(self.R.T@self.R,np.eye(3),atol=1e-5) or not np.isclose(np.linalg.det(self.R),1):raise ValueError('Invalid camera transform')
  self.C=-self.R.T@self.t
  if abs(self.C[2])<1:raise ValueError('Camera is on board plane')
  if len(data.get('image_size',[]))!=2 or any(type(v)!=int or v<=0 for v in data['image_size']):raise ValueError('Invalid calibration resolution')
  h=data.get('tag_height_mm')
  if h is None or not math.isfinite(h) or not 0<=h<abs(self.C[2]):raise ValueError('Measured tag height required')
  off=data.get('centre_offset_mm')
  if not isinstance(off,list) or len(off)!=2 or not all(math.isfinite(v) for v in off):raise ValueError('Measured tag offset required')
  a=data.get('arena',{})
  if not all(isinstance(a.get(k),(int,float)) and math.isfinite(a[k]) for k in ('x_mm','y_mm','width_mm','height_mm')):raise ValueError('Arena placement required')
  if a['x_mm']<0 or a['y_mm']<0 or min(a['width_mm'],a['height_mm'])<=0 or a['x_mm']+a['width_mm']>914.400001 or a['y_mm']+a['height_mm']>508.000001:raise ValueError('Arena exceeds physical board')
 @classmethod
 def load(cls,path):return cls(json.loads(Path(path).read_text()))
 def image_to_board(self,points_px,height_mm):
  if not math.isfinite(height_mm) or not 0<=height_mm<abs(self.C[2]):raise ValueError('Marker plane is above camera')
  pts=np.asarray(points_px,float).reshape(-1,1,2)
  if not np.isfinite(pts).all():raise ValueError('Invalid image points')
  uv=cv2.undistortPoints(pts,self.K,self.D).reshape(-1,2)
  rays=np.c_[uv,np.ones(len(uv))]@self.R
  plane=math.copysign(height_mm,self.C[2])
  if np.any(abs(rays[:,2])<1e-9):raise ValueError('Ray parallel to board')
  scale=(plane-self.C[2])/rays[:,2]
  if np.any(scale<=0):raise ValueError('Points behind camera')
  return (self.C+scale[:,None]*rays)[:,:2]
 def tag_to_rover(self,corners_px,tag_height_mm,centre_offset_mm):
  points=self.image_to_board(corners_px,tag_height_mm)
  centre=points.mean(axis=0);front=points[:2].mean(axis=0)-centre
  if np.linalg.norm(front)<.01:raise ValueError('Degenerate marker')
  heading=math.atan2(front[1],front[0]);forward,right=centre_offset_mm
  centre+=np.array([forward*math.cos(heading)-right*math.sin(heading),forward*math.sin(heading)+right*math.cos(heading)])
  return Pose(float(centre[0]),float(centre[1]),heading)
 def save(self,path):
  path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(self.data,indent=2));tmp.replace(path)
