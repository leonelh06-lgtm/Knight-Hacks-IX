import asyncio, unittest, time, socket
from queue import Queue
from types import SimpleNamespace
from rover.__main__ import run_runtime, load_setup, parse_args
from rover.types import Pose,PoseSample
from test_rover_pursuit import game,config
class Tracker:
 closed=False
 def __init__(self,*a,**k):pass
 def start(self):pass
 def latest(self):return PoseSample(Pose(457,254,0),time.monotonic(),True)
 def close(self):self.closed=True
class Cal:
 data=dict(camera='1',image_size=[1280,720],projection_size=[1280,720],calibration_id='c',verified=True,validation_error_mm=5,tag_height_mm=177.8,arena=game()['arena'])
class Tests(unittest.IsolatedAsyncioTestCase):
 def args(self,port=0,**kw):
  d=dict(camera=1,tag_id=0,camera_backend='auto',game_state_port=port,rover_state_port=0,dry_run=True,frames=4);d.update(kw);return SimpleNamespace(**d)
 async def test_dry_run_never_creates_motor_link(self):
  def forbidden(*a,**k):raise AssertionError('Dry run connected BLE')
  q=Queue()
  result=await run_runtime(self.args(),config(),Cal(),tracker_factory=Tracker,link_factory=forbidden,commands=q)
  self.assertFalse(result.armed);self.assertEqual(result.command,b'X')
 async def test_terminal_closure_and_bind_failure(self):
  q=Queue();q.put('EOF')
  result=await run_runtime(self.args(frames=0),config(),Cal(),tracker_factory=Tracker,commands=q);self.assertEqual(result.command,b'X')
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
   s.bind(('127.0.0.1',0))
   with self.assertRaises(OSError):await run_runtime(self.args(s.getsockname()[1]),config(),Cal(),tracker_factory=Tracker,commands=Queue())
 async def test_camera_and_ble_error_cleanup(self):
  class BadTracker(Tracker):
   def latest(self):return PoseSample(None,0,False,'camera failed')
  with self.assertRaises(RuntimeError):await run_runtime(self.args(),config(),Cal(),tracker_factory=BadTracker,commands=Queue())
  class BadLink:
   def __init__(self,*a,**k):self.connected=False
   async def run(self,stop):raise RuntimeError('BLE failed')
   def request_stop(self):pass
  with self.assertRaises(RuntimeError):await run_runtime(self.args(dry_run=False),config(),Cal(),tracker_factory=Tracker,link_factory=BadLink,commands=Queue())
 def test_bad_setup_rejected_before_resources(self):
  from unittest.mock import patch
  for overrides in [dict(camera=2),dict(tag_id=1)]:
   with patch('rover.__main__.BoardCalibration.load',return_value=Cal()),patch('rover.__main__.read_config',return_value={**config(),'tag_id':0}):
    with self.assertRaises(ValueError):load_setup(SimpleNamespace(config='x',calibration='x',**vars(self.args(**overrides))))
  with self.assertRaises(FileNotFoundError):load_setup(SimpleNamespace(config='missing-file',calibration='missing-calibration',**vars(self.args())))
 def test_cli_has_calibration_and_dry_run_modes(self):
  args=parse_args(['--dry-run','--camera','1','--tag-id','0']);self.assertTrue(args.dry_run);self.assertEqual(args.camera,1)
if __name__=='__main__':unittest.main()
