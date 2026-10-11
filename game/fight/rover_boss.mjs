// Autonomous physical boss; gameplay policy remains independent of tracking.
export function toBoardPlayer(hero,room,arena,radius) {
 const sx=arena.width_mm/(room.maxX-room.minX),sy=arena.height_mm/(room.maxZ-room.minZ);
 return {x_mm:arena.x_mm+(hero.position.x-room.minX)*sx,y_mm:arena.y_mm+(hero.position.z-room.minZ)*sy,radius_mm:radius*Math.max(sx,sy)};
}
export function roverEligible(state,calibration) {
 return !!(calibration?.verified && !state.projectionInvalid && state.physicalBoss && state.started && !state.terminal && !state.paused && state.visible &&
 calibration.projection_size?.length===2 && state.projectionSize.every((n,i)=>n===calibration.projection_size[i]));
}
export function createRoverBoss({policy='end_level',onDefeat=()=>{}}={}) {
 let session=null,calibration=null,terminal=false;const seen=new Set();
 return {
  reset(sessionId,calibrationId){session=sessionId;calibration=calibrationId;seen.clear();terminal=false;},
  handleContact(event) {
   if(event.session_id!==session||event.calibration_id!==calibration)return false;
   if(seen.has(event.event_id))return true;
   seen.add(event.event_id);
   if(!terminal) {
    if(policy==='end_level'){terminal=true;onDefeat(event);}
    else if(typeof policy==='function')policy(event);
    else throw new Error('Unknown rover contact policy');
   }
   return true;
  },
  get terminal(){return terminal;}
 };
}
