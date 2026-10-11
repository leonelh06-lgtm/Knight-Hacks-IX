"""Overhead capture/detection runs separately from the motor heartbeat."""
import threading,time
from .types import PoseSample
from .camera_guard import CameraGuard
from gesture_control.tracking import open_camera

def unique_marker(corners,ids,tag_id):
 matches=[c for c,i in zip(corners,ids) if int(i[0])==tag_id]
 return matches[0] if len(matches)==1 else None

class OverheadTracker:
 def __init__(self,camera,tag_id,calibration,backend='auto'):
  self.camera,self.tag_id,self.calibration,self.backend=camera,tag_id,calibration,backend
  self._sample=PoseSample(None,0,False);self._lock=threading.Lock();self._stop=threading.Event();self._thread=threading.Thread(target=self._run,daemon=True)
 def start(self):self._thread.start()
 def latest(self):
  with self._lock:return self._sample
 def _publish(self,sample):
  with self._lock:self._sample=sample
 def close(self):
  self._stop.set()
  if self._thread.ident:self._thread.join(2)
 def _run(self):
  cap=None
  try:
   import cv2,numpy as np
   cap=open_camera(self.camera,self.backend);cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
   guard=CameraGuard(self.calibration)
   dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
   detector=cv2.aruco.ArucoDetector(dictionary,cv2.aruco.DetectorParameters())
   while not self._stop.is_set():
    captured=time.monotonic();ok,frame=cap.read()
    if not ok or frame is None:raise RuntimeError('Overhead camera stopped')
    height,width=frame.shape[:2]
    if [width,height]!=self.calibration.data['image_size']:raise RuntimeError('Camera resolution changed; recalibrate')
    corners,ids,_=detector.detectMarkers(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY))
    if not guard.check(corners,ids):
     self._publish(PoseSample(None,captured,False))
     continue
    marker=unique_marker(corners,ids,self.tag_id) if ids is not None else None
    pose=None
    if marker is not None:
     try:
      pose=self.calibration.tag_to_rover(marker.reshape(4,2),self.calibration.data['tag_height_mm'],self.calibration.data['centre_offset_mm'])
     except ValueError:pass
    self._publish(PoseSample(pose,captured,pose is not None))
  except Exception as error:self._publish(PoseSample(None,0,False,str(error)))
  finally:
   if cap is not None:cap.release()
