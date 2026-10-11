from dataclasses import dataclass
@dataclass(frozen=True)
class Pose:
 x_mm:float
 y_mm:float
 heading_rad:float
@dataclass(frozen=True)
class PoseSample:
 pose:Pose|None
 captured_at:float
 valid:bool
 error:str=''
