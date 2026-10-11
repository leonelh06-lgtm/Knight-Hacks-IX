"""Interactive calibration; never connects to motors."""
import json,uuid
from pathlib import Path
import cv2,numpy as np
from gesture_control.tracking import open_camera
from .calibration import BoardCalibration

def calibrate_intrinsics(camera,backend,output,cols,rows,square_mm):
 if min(cols,rows)<3 or square_mm<=0:raise ValueError('Measured checkerboard geometry required')
 cap=open_camera(camera,backend);objects=[];images=[];size=None
 obj=np.zeros((cols*rows,3),np.float32);obj[:,:2]=np.mgrid[0:cols,0:rows].T.reshape(-1,2)*square_mm
 try:
  print('Show checkerboard at different positions/tilts. Space records; Enter solves after 12 views; Q cancels.',flush=True)
  while True:
   ok,frame=cap.read()
   if not ok:raise RuntimeError('Camera failed')
   gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY);size=(gray.shape[1],gray.shape[0]);found,corners=cv2.findChessboardCorners(gray,(cols,rows))
   if found:cv2.drawChessboardCorners(frame,(cols,rows),corners,True)
   cv2.putText(frame,f'Views {len(images)}/12',(20,30),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,255,255),2);cv2.imshow('Intrinsics calibration',frame);key=cv2.waitKey(10)&255
   if key in (ord('q'),27):raise RuntimeError('Calibration cancelled')
   if key==32 and found:
    corners=cv2.cornerSubPix(gray,corners,(11,11),(-1,-1),(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,30,.001));images.append(corners);objects.append(obj.copy())
   if key in (10,13) and len(images)>=12:break
  rms,K,D,_,_=cv2.calibrateCamera(objects,images,size,None,None)
  if not np.isfinite(rms) or rms>2:raise ValueError(f'Intrinsics RMS {rms:.2f}px too high; collect better views')
  data={'version':1,'camera':str(camera),'image_size':list(size),'camera_matrix':K.tolist(),'distortion':D.flatten().tolist(),'intrinsics_rms_px':float(rms)}
  Path(output).write_text(json.dumps(data,indent=2));print(f'Intrinsics saved; RMS {rms:.2f}px',flush=True)
 finally:cap.release();cv2.destroyAllWindows()

def calibrate_board(camera,backend,intrinsics,output,tag_height_mm,offset,arena,projection_size):
 data=json.loads(Path(intrinsics).read_text())
 if data['camera']!=str(camera):raise ValueError('Intrinsics belong to another camera')
 cap=open_camera(camera,backend);points=[];window='Physical board corners'
 def click(event,x,y,flags,param):
  if event==cv2.EVENT_LBUTTONDOWN and len(points)<4:points.append((x,y))
 cv2.namedWindow(window);cv2.setMouseCallback(window,click)
 try:
  while len(points)<4:
   ok,frame=cap.read()
   if not ok:raise RuntimeError('Camera failed')
   if [frame.shape[1],frame.shape[0]]!=data['image_size']:raise ValueError('Intrinsics resolution changed')
   cv2.putText(frame,['Click physical board TOP-LEFT','Click TOP-RIGHT','Click BOTTOM-RIGHT','Click BOTTOM-LEFT'][len(points)],(15,30),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,255,255),2)
   for p in points:cv2.circle(frame,p,5,(0,255,255),2)
   cv2.imshow(window,frame)
   if cv2.waitKey(10)&255 in (ord('q'),27):raise RuntimeError('Calibration cancelled')
  world=np.array([[0,0,0],[914.4,0,0],[914.4,508,0],[0,508,0]],float);image=np.asarray(points,float)
  K=np.asarray(data['camera_matrix']);D=np.asarray(data['distortion']);ok,rvecs,tvecs,_=cv2.solvePnPGeneric(world,image,K,D,flags=cv2.SOLVEPNP_IPPE)
  candidates=[]
  for r,t in zip(rvecs,tvecs):
   R=cv2.Rodrigues(r)[0];cam=world@R.T+t.reshape(3)
   if np.any(cam[:,2]<=0):continue
   projected=cv2.projectPoints(world,r,t,K,D)[0].reshape(-1,2);err=float(np.sqrt(np.mean((projected-image)**2)))
   candidates.append((err,R,t.reshape(3)))
  if not candidates:raise ValueError('No positive-depth board pose')
  candidates.sort(key=lambda c:c[0]);err,R,t=candidates[0]
  if err>2:raise ValueError('Board reprojection error too high')
  if len(candidates)>1 and abs(candidates[1][0]-err)<.05 and not np.allclose(R,candidates[1][1],atol=.01):raise ValueError('Ambiguous board pose; use more tilted view or improve corner calibration')
  data.update(projection_size=list(projection_size),calibration_id=str(uuid.uuid4()),rotation=R.tolist(),translation=t.tolist(),tag_height_mm=tag_height_mm,centre_offset_mm=list(offset),arena=arena,validation_error_mm=None,verified=False)
  BoardCalibration(data).save(output);print('Board calibration saved. Validate measured tag locations before arming.',flush=True)
 finally:cap.release();cv2.destroyAllWindows()

def validate_calibration(camera,backend,calibration,tag_id):
 from .vision import unique_marker
 c=BoardCalibration.load(calibration)
 if c.data['camera']!=str(camera):raise ValueError('Wrong calibration camera')
 cap=open_camera(camera,backend);detector=cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11),cv2.aruco.DetectorParameters());measured=[]
 try:
  print('Use only the rover tag. Keep camera and projector fixed during validation and play.',flush=True)
  print('Measure rover centre at table centre and near each corner of usable area. Space captures, Enter finishes after 5 locations, Q cancels.',flush=True)
  while True:
   ok,frame=cap.read()
   if not ok:raise RuntimeError('Camera failed')
   if [frame.shape[1],frame.shape[0]]!=c.data['image_size']:raise ValueError('Camera resolution changed')
   corners,ids,_=detector.detectMarkers(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY));marker=unique_marker(corners,ids,tag_id) if ids is not None else None
   pose=c.tag_to_rover(marker.reshape(4,2),c.data['tag_height_mm'],c.data['centre_offset_mm']) if marker is not None else None
   cv2.imshow('Reference validation',frame);key=cv2.waitKey(10)&255
   if key in (ord('q'),27):raise RuntimeError('Validation cancelled')
   if key==32 and pose:
    x,y=map(float,input('Measured rover-centre x_mm y_mm: ').split());measured.append([x,y,pose.x_mm,pose.y_mm])
   if key in (10,13) and len(measured)>=5:break
  a=np.asarray(measured)
  if np.any(a[:,:2]<0) or np.any(a[:,:2]>[914.4,508]) or not np.isfinite(a).all():raise ValueError('Invalid reference measurements')
  if np.ptp(a[:,0])<300 or np.ptp(a[:,1])<150:raise ValueError('References must span centre and corners of board')
  error=float(np.max(np.linalg.norm(a[:,:2]-a[:,2:],axis=1)))
  if error>20:raise ValueError(f'Validation error {error:.1f} mm exceeds 20mm. Recalibrate.')
  c.data.pop('camera_guard',None)
  c.data.update(validation_error_mm=error,validation_references=measured,verified=True);c.save(calibration);print(f'Validated max error {error:.1f}mm',flush=True)
 finally:cap.release();cv2.destroyAllWindows()
