"""Pure autonomous pursuit; all deadlines use this process's monotonic clock."""
from dataclasses import dataclass
import math
import uuid
from .protocol import validate_message, number
from .geometry import edge_clearance_mm, footprints_overlap

@dataclass(frozen=True)
class Decision:
    command: bytes
    armed: bool
    status: str
    contact_event: dict | None = None

class PursuitController:
    def __init__(self, config):
        self.config=config
        self.game=None
        self.received_at=0.
        self.pose=None
        self.armed=False
        self.status='waiting'
        self.turn=None
        self.contact=None
        self.contact_latched=False

    def update_game(self, message, received_at):
        try: validate_message(message)
        except (ValueError,TypeError,AttributeError):
            self.disarm('invalid game state');return False
        if message['type']!='game_state':return False
        previous=self.game
        changed=previous and any(previous[k]!=message[k] for k in ('session_id','calibration_id','arena','level_id'))
        if previous and not changed and message['seq']<=previous['seq']:return False
        if changed:
            self.disarm('encounter changed')
            # Only a different session can release the contact latch.
            if previous['session_id']!=message['session_id']:
                self.contact=None;self.contact_latched=False
        self.game=message
        self.received_at=received_at
        if not message['active'] or message['terminal'] or not message['physical_boss']:
            self.disarm('game inactive')
        return True

    def update_pose(self, sample):
        self.pose=sample

    def disarm(self, reason='manual stop'):
        self.armed=False;self.status=reason;self.turn=None

    def ack_contact(self, event_id):
        if self.contact and self.contact['event_id']==event_id:self.contact=None

    def _problem(self, now):
        c=self.config;g=self.game;s=self.pose
        try:
            if c.get('verified') is not True or c.get('calibration_verified') is not True:return 'measurements unverified'
            number(c.get('stopping_distance_mm'),0,914.4)
            number(c.get('validation_error_mm'),0,20)
            number(c.get('extra_margin_mm'),0,508)
            number(c['footprint']['length_mm'],.01,914.4);number(c['footprint']['width_mm'],.01,508)
        except (ValueError,TypeError,KeyError):return 'invalid measurements'
        if not g or not g['physical_boss'] or g['level_id']!='boss-arena' or not g['active'] or g['terminal']:return 'game inactive'
        if g['calibration_id']!=c.get('calibration_id') or g['arena']!=c.get('arena'):return 'calibration mismatch'
        if not 0<=now-self.received_at<=.5:return 'game stale'
        if not s or not s.valid or not s.pose or not 0<=now-s.captured_at<=.25:return 'tracking stale'
        p=s.pose
        if not all(math.isfinite(v) for v in (p.x_mm,p.y_mm,p.heading_rad)):return 'invalid pose'
        if edge_clearance_mm(p,c['footprint'],c['board'])<=self.margin:return 'table edge'
        if self.contact_latched:return 'contact latched'
        return None

    @property
    def margin(self):
        return self.config['stopping_distance_mm']+self.config['validation_error_mm']+self.config['extra_margin_mm']+self.config.get('guard_error_mm',0)

    def arm(self, now):
        problem=self._problem(now)
        if problem:self.disarm(problem);return False
        self.armed=True;self.status='armed';self.turn=None;return True

    def tick(self, now):
        problem=self._problem(now)
        if problem:self.disarm(problem)
        if not self.armed:return Decision(b'X',False,self.status,self.contact)
        p=self.pose.pose;g=self.game;f=self.config['footprint']
        if footprints_overlap(p,f['length_mm'],f['width_mm'],g['player']):
            self.contact_latched=True
            self.contact=dict(type='rover_contact',version=1,session_id=g['session_id'],calibration_id=g['calibration_id'],level_id=g['level_id'],event_id=str(uuid.uuid4()))
            self.disarm('contact latched')
            return Decision(b'X',False,self.status,self.contact)
        # Keep target in a safe region even when the projected player hugs an edge.
        # Circumscribed footprint accounts for any rotation during a turn.
        inset=math.hypot(f['length_mm']/2,f['width_mm']/2)+self.margin
        board=self.config['board']
        if inset*2>=min(board.values()):
            self.disarm('safe region empty');return Decision(b'X',False,self.status)
        x=min(max(g['player']['x_mm'],inset),board['width_mm']-inset)
        y=min(max(g['player']['y_mm'],inset),board['height_mm']-inset)
        dx,dy=x-p.x_mm,y-p.y_mm
        if math.hypot(dx,dy)<10:
            self.status='target outside reach';return Decision(b'X',True,self.status)
        error=math.atan2(math.sin(math.atan2(dy,dx)-p.heading_rad),math.cos(math.atan2(dy,dx)-p.heading_rad))
        if self.turn and abs(error)<.15:self.turn=None
        if abs(error)>.30:self.turn=b'D' if error>0 else b'A'
        command=self.turn or b'W'
        # A turn can increase the footprint beyond its current corners.
        if command in (b'A',b'D') and min(p.x_mm,p.y_mm,board['width_mm']-p.x_mm,board['height_mm']-p.y_mm)<=inset:
            self.disarm('unsafe turn');return Decision(b'X',False,self.status)
        self.status='pursuing'
        return Decision(command,True,self.status)
