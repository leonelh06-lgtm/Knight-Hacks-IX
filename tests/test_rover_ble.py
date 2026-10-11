import unittest,asyncio,time
from rover.ble import MotorLink,CHARACTERISTIC
from rover.pursuit import Decision
class Fake:
 def __init__(self, fail=False, stall=False):self.writes=[];self.is_connected=False;self.fail=fail;self.stall=stall;self.disconnected=False
 async def connect(self):self.is_connected=True
 async def disconnect(self):self.is_connected=False;self.disconnected=True
 async def write_gatt_char(self,char,data,response):
  assert char==CHARACTERISTIC and response is False
  self.writes.append(data)
  if self.stall:await asyncio.sleep(10)
  if self.fail and data!=b'X':raise OSError('lost')
class Tests(unittest.IsolatedAsyncioTestCase):
 async def test_heartbeat_and_stop(self):
  f=Fake();stop=asyncio.Event();source=lambda:Decision(b'W',True,'pursuing')
  link=MotorLink('robot',source,client_factory=lambda _:f)
  t=asyncio.create_task(link.run(stop));await asyncio.sleep(.24);link.request_stop();stop.set();await t
  self.assertGreaterEqual(f.writes.count(b'W'),2);self.assertEqual(f.writes[0],b'X');self.assertEqual(f.writes[-1],b'X');self.assertTrue(f.disconnected)
 async def test_disarmed_and_stale_detection(self):
  f=Fake();stop=asyncio.Event();start=time.monotonic()
  def source():return Decision(b'W',True,'pursuing') if time.monotonic()-start<.12 else Decision(b'X',False,'tracking stale')
  link=MotorLink('robot',source,client_factory=lambda _:f);t=asyncio.create_task(link.run(stop));await asyncio.sleep(.34);stop.set();await t
  self.assertEqual(f.writes[-2:], [b'X',b'X'])
 async def test_timeout_and_link_loss(self):
  for kwargs in [dict(fail=True),dict(stall=True)]:
   f=Fake(**kwargs);faults=[];link=MotorLink('robot',lambda:Decision(b'W',True,'go'),client_factory=lambda _:f,on_fault=faults.append)
   with self.assertRaises((OSError,TimeoutError)):await link.run(asyncio.Event())
   self.assertTrue(f.disconnected);self.assertTrue(faults);self.assertFalse(link.connected)
 async def test_cancel_and_source_failure(self):
  f=Fake();link=MotorLink('robot',lambda:Decision(b'W',True,'go'),client_factory=lambda _:f)
  t=asyncio.create_task(link.run(asyncio.Event()));await asyncio.sleep(.02);t.cancel()
  with self.assertRaises(asyncio.CancelledError):await t
  self.assertEqual(f.writes[-1],b'X');self.assertTrue(f.disconnected)
  f=Fake();faults=[]
  def bad():raise ValueError('broken intent')
  link=MotorLink('robot',bad,client_factory=lambda _:f,on_fault=faults.append)
  with self.assertRaises(ValueError):await link.run(asyncio.Event())
  self.assertNotIn(b'W',f.writes);self.assertTrue(faults)
if __name__=='__main__':unittest.main()
