"""Fixed references bound camera-induced error over the whole playing board."""
import numpy as np
import cv2

MAX_CAMERA_DRIFT_MM=4.

class CameraGuard:
    def __init__(self, calibration):
        self.calibration=calibration
        markers=calibration.data.get('camera_guard',{}).get('markers',[])
        if len(markers)!=2:raise ValueError('Two fixed reference tags required')
        self.ids=[m['tag_id'] for m in markers]
        if any(type(i)!=int or not 0<=i<587 for i in self.ids) or len(set(self.ids))!=2:raise ValueError('Invalid reference tag IDs')
        self.baseline=np.asarray([m['corners_px'] for m in markers],float)
        if self.baseline.shape!=(2,4,2) or not np.isfinite(self.baseline).all():raise ValueError('Invalid reference corners')
        xy=calibration.image_to_board(self.baseline.reshape(-1,2),0)
        if np.ptp(xy[:,0])<300 or np.ptp(xy[:,1])<150:raise ValueError('Fixed reference tags must span at least 300 by 150mm')
        self.world=np.c_[xy,np.zeros(len(xy))]
        self.rvec=cv2.Rodrigues(calibration.R)[0]
        self.grid=np.array([[x,y] for x in (0,457.2,914.4) for y in (0,254,508)],float)

    def check(self,corners,ids):
        if ids is None:return False
        current=[]
        for tag_id in self.ids:
            matches=[c for c,i in zip(corners,ids) if int(i[0])==tag_id]
            if len(matches)!=1:return False
            current.append(matches[0])
        c=self.calibration
        image=np.asarray(current,float).reshape(-1,2)
        ok,r,t=cv2.solvePnP(self.world,image,c.K,c.D,self.rvec.copy(),c.t.copy().reshape(3,1),True,flags=cv2.SOLVEPNP_ITERATIVE)
        if not ok:raise ValueError('Camera reference pose failed; recalibrate')
        predicted=cv2.projectPoints(self.world,r,t,c.K,c.D)[0].reshape(-1,2)
        if np.max(np.linalg.norm(predicted-image,axis=1))>2:raise ValueError('Camera reference inconsistent; recalibrate')
        R=cv2.Rodrigues(r)[0]
        C=-R.T@t.reshape(3)
        if C[2]*c.C[2]<=0 or abs(C[2])<=c.data['tag_height_mm']:raise ValueError('Camera moved across marker plane; recalibrate')
        worst=0.
        for height in (0,c.data['tag_height_mm']):
            world=np.c_[self.grid,np.full(len(self.grid),np.copysign(height,c.C[2]))]
            if np.any((world@R.T+t.reshape(3))[:,2]<=0):raise ValueError('Camera moved behind board; recalibrate')
            pixels=cv2.projectPoints(world,r,t,c.K,c.D)[0].reshape(-1,2)
            recovered=c.image_to_board(pixels,height)
            worst=max(worst,float(np.max(np.linalg.norm(recovered-self.grid,axis=1))))
        if worst>MAX_CAMERA_DRIFT_MM:raise ValueError(f'Camera/reference moved: board error {worst:.1f}mm; recalibrate')
        return True
