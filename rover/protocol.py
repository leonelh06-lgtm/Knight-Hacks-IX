"""Board-space version 1 messages; no cross-process clock assumptions."""
import math

def number(x, lo=-1e7, hi=1e7):
 if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not lo<=x<=hi: raise ValueError('Invalid finite number')
 return x

def text(x):
 if not isinstance(x,str) or not 0<len(x)<=128:raise ValueError('Invalid identifier')

def validate_message(m):
 if not isinstance(m,dict) or m.get('version')!=1: raise ValueError('Unsupported message')
 kind=m.get('type')
 if kind not in ('game_state','rover_state','rover_contact','contact_ack','claim_game'):raise ValueError('Unknown type')
 text(m.get('session_id'))
 if kind=='claim_game':return m
 text(m.get('calibration_id'))
 if kind in ('game_state','rover_state'):
  seq=number(m.get('seq'),0,2**53-1)
  if not isinstance(seq,int):raise ValueError('Sequence must be integer')
 if kind=='game_state':
  text(m.get('level_id'))
  for k in ('active','terminal','physical_boss'):
   if not isinstance(m.get(k),bool):raise ValueError('Boolean required')
  a=m.get('arena',{});p=m.get('player',{})
  x=number(a.get('x_mm'),0,914.4);y=number(a.get('y_mm'),0,508)
  w=number(a.get('width_mm'),.01,914.4);h=number(a.get('height_mm'),.01,508)
  if x+w>914.400001 or y+h>508.000001:raise ValueError('Arena exceeds board')
  number(p.get('x_mm'),x,x+w);number(p.get('y_mm'),y,y+h);number(p.get('radius_mm'),.01,min(w,h)/2)
 elif kind=='rover_state':
  text(m.get('run_id'))
  for k in ('valid','armed'):
   if not isinstance(m.get(k),bool):raise ValueError('Boolean required')
  text(m.get('status'));number(m.get('frame_age_ms'),0,60000)
  f=m.get('footprint',{});number(f.get('length_mm'),.01,914.4);number(f.get('width_mm'),.01,508)
  if m['valid']:
   p=m.get('pose',{});number(p.get('x_mm'),0,914.4);number(p.get('y_mm'),0,508);number(p.get('heading_rad'),-math.pi,math.pi)
 elif kind=='rover_contact':text(m.get('event_id'));text(m.get('level_id'))
 elif kind=='contact_ack':text(m.get('event_id'))
 return m
