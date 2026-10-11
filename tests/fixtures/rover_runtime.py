"""Test harness: real UDP runtime, synthetic camera, injected fake BLE only."""
import sys,time,threading,asyncio
from types import SimpleNamespace
from queue import Queue
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rover.__main__ import run_runtime
from rover.ble import MotorLink
from rover.types import Pose,PoseSample
from test_rover_pursuit import config
from test_rover_integration import Cal
mode='fresh'
class Tracker:
 def __init__(self,*a,**k):pass
 def start(self):pass
 def close(self):pass
 def latest(self):return PoseSample(Pose(700 if mode=='contact' else 457,254,0),time.monotonic()-(1 if mode=='stall' else 0),True)
class Fake:
 is_connected=False
 async def connect(self):self.is_connected=True
 async def disconnect(self):self.is_connected=False
 async def write_gatt_char(self,char,data,response=False):print('MOCK MOTOR '+data.decode(),flush=True)
def link(name,source,**kw):return MotorLink(name,source,client_factory=lambda _:Fake(),**kw)
q=Queue()
def read():
 global mode
 for line in sys.stdin:
  text=line.strip()
  if text in ('stall','resume','contact'):mode='fresh' if text=='resume' else text
  else:q.put(text)
 q.put('EOF')
threading.Thread(target=read,daemon=True).start()
args=SimpleNamespace(camera=1,tag_id=0,camera_backend='auto',game_state_port=int(sys.argv[1]),rover_state_port=int(sys.argv[2]),dry_run=False,frames=0)
asyncio.run(run_runtime(args,config(),Cal(),tracker_factory=Tracker,link_factory=link,commands=q))
