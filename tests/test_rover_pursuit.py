import unittest, math
from rover.pursuit import PursuitController
from rover.types import Pose, PoseSample
from rover.geometry import footprints_overlap, edge_clearance_mm
def game(session='s', seq=0, **kw):
 d=dict(type='game_state',version=1,session_id=session,calibration_id='c',seq=seq,level_id='boss-arena',physical_boss=True,active=True,terminal=False,arena=dict(x_mm=0,y_mm=0,width_mm=914.4,height_mm=508),player=dict(x_mm=700,y_mm=254,radius_mm=10));d.update(kw);return d
def config(**kw):
 d=dict(board=dict(width_mm=914.4,height_mm=508),footprint=dict(length_mm=177.8,width_mm=177.8),verified=True,stopping_distance_mm=20,extra_margin_mm=10,calibration_id='c',calibration_verified=True,validation_error_mm=5,arena=game()['arena']);d.update(kw);return d
class Tests(unittest.TestCase):
 def setup(self, **kw):
  c=PursuitController(config(**kw));c.update_game(game(),0);c.update_pose(PoseSample(Pose(457.2,254,0),0,True));return c
 def test_eligibility(self):
  c=self.setup();self.assertEqual(c.tick(0).command,b'X');self.assertTrue(c.arm(0));self.assertEqual(c.tick(0).command,b'W')
  for override in [dict(active=False),dict(physical_boss=False,level_id='hedge-maze'),dict(physical_boss=False,level_id='ruins'),dict(terminal=True)]:
   c=self.setup();c.update_game(game(seq=1,**override),0);self.assertFalse(c.arm(0));self.assertEqual(c.tick(0).command,b'X')
  for override in [dict(verified=False),dict(calibration_verified=False),dict(stopping_distance_mm=None)]:
   self.assertFalse(self.setup(**override).arm(0))
 def test_freshness_and_rearm(self):
  for age in [.251,.501]:
   c=self.setup();c.arm(0)
   if age>.5:c.update_pose(PoseSample(Pose(457,254,0),age,True))
   self.assertEqual(c.tick(age).command,b'X');self.assertFalse(c.tick(age).armed)
   c.update_game(game(seq=1),age);c.update_pose(PoseSample(Pose(457,254,0),age,True));self.assertEqual(c.tick(age).command,b'X')
 def test_changed_session_and_calibration(self):
  for override in [dict(session_id='new'),dict(calibration_id='other'),dict(arena=dict(x_mm=10,y_mm=0,width_mm=900,height_mm=508))]:
   c=self.setup();c.arm(0);c.update_game(game(seq=1,**override),0);self.assertFalse(c.tick(0).armed)
 def test_turn_hysteresis_quadrants(self):
  for heading,command in [(0,b'W'),(math.pi/2,b'A'),(-math.pi/2,b'D'),(math.pi,b'A')]:
   c=self.setup();c.update_pose(PoseSample(Pose(457,254,heading),0,True));c.arm(0);self.assertEqual(c.tick(0).command,command)
  c=self.setup();c.update_pose(PoseSample(Pose(457,254,-.4),0,True));c.arm(0);self.assertEqual(c.tick(0).command,b'D')
  c.update_pose(PoseSample(Pose(457,254,-.2),0,True));self.assertEqual(c.tick(0).command,b'D')
  c.update_pose(PoseSample(Pose(457,254,-.1),0,True));self.assertEqual(c.tick(0).command,b'W')
 def test_edge_and_unreachable_target(self):
  c=self.setup();c.update_pose(PoseSample(Pose(110,254,0),0,True));self.assertFalse(c.arm(0))
  c=self.setup();c.update_game(game(seq=1,player=dict(x_mm=900,y_mm=254,radius_mm=1)),0);c.arm(0);self.assertEqual(c.tick(0).command,b'W')
  c.update_pose(PoseSample(Pose(800,254,0),0,True));self.assertEqual(c.tick(0).command,b'X');self.assertFalse(c.tick(0).armed)
  self.assertLess(edge_clearance_mm(Pose(110,254,math.pi/4),config()['footprint'],config()['board']),0)
 def test_contact_latch_ack_and_new_encounter(self):
  c=self.setup();c.update_game(game(seq=1,player=dict(x_mm=546.1,y_mm=254,radius_mm=0.01)),0);c.arm(0)
  first=c.tick(0);self.assertEqual(first.command,b'X');self.assertIsNotNone(first.contact_event);self.assertFalse(first.armed)
  self.assertEqual(c.tick(0).contact_event,first.contact_event);c.ack_contact(first.contact_event['event_id']);self.assertIsNone(c.tick(0).contact_event);self.assertFalse(c.arm(0))
  c.update_game(game('new'),0);self.assertTrue(c.arm(0))
 def test_rotated_and_tangent_contact(self):
  p=Pose(200,200,math.pi/4)
  self.assertTrue(footprints_overlap(p,100,40,dict(x_mm=200+50/math.sqrt(2),y_mm=200+50/math.sqrt(2),radius_mm=1)))
  self.assertTrue(footprints_overlap(Pose(200,200,0),100,40,dict(x_mm=260,y_mm=200,radius_mm=10)))
  self.assertFalse(footprints_overlap(p,100,40,dict(x_mm=260,y_mm=200,radius_mm=1)))
if __name__=='__main__':unittest.main()
