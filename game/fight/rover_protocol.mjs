export function validateRoverMessage(m) {
 const fail=()=>{throw new TypeError('Invalid rover message');};
 const text=v=>{if(typeof v!=='string'||!v.length||v.length>128)fail();};
 const num=(v,lo=-1e7,hi=1e7)=>{if(typeof v!=='number'||!Number.isFinite(v)||v<lo||v>hi)fail();return v;};
 const bool=v=>{if(typeof v!=='boolean')fail();};
 if(!m||typeof m!=='object'||m.version!==1)fail();
 if(!['game_state','rover_state','rover_contact','contact_ack','claim_game'].includes(m.type))fail();
 text(m.session_id);if(m.type==='claim_game')return m;text(m.calibration_id);
 if(['game_state','rover_state'].includes(m.type)){num(m.seq,0,Number.MAX_SAFE_INTEGER);if(!Number.isInteger(m.seq))fail();}
 if(m.type==='game_state'){
  text(m.level_id);['active','terminal','physical_boss'].forEach(k=>bool(m[k]));const a=m.arena??{},p=m.player??{};
  num(a.x_mm,0,914.4);num(a.y_mm,0,508);num(a.width_mm,.01,914.4);num(a.height_mm,.01,508);
  if(a.x_mm+a.width_mm>914.400001||a.y_mm+a.height_mm>508.000001)fail();
  num(p.x_mm,a.x_mm,a.x_mm+a.width_mm);num(p.y_mm,a.y_mm,a.y_mm+a.height_mm);num(p.radius_mm,.01,Math.min(a.width_mm,a.height_mm)/2);
 }else if(m.type==='rover_state'){
  bool(m.valid);bool(m.armed);text(m.status);num(m.frame_age_ms,0,60000);
  num(m.footprint?.length_mm,.01,914.4);num(m.footprint?.width_mm,.01,508);
  if(m.valid){num(m.pose?.x_mm,0,914.4);num(m.pose?.y_mm,0,508);num(m.pose?.heading_rad,-Math.PI,Math.PI);}
 }else{ text(m.event_id);if(m.type==='rover_contact')text(m.level_id);}
 return m;
}
