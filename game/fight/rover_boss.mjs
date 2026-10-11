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

// All coordinates are board millimetres; rendering and motor control are separate.
export function createRoverProjectiles({warning=.7, speed=280, cooldown=1.2, lead=.7}={}) {
 const state={phase:'waiting',bullets:[],target:null,playerHP:100,bossHP:3,blocked:0};
 let phaseAt=0,last=null,previousPlayer=null;
 function reset() {
  Object.assign(state,{phase:'waiting',bullets:[],target:null,playerHP:100,bossHP:3,blocked:0});
  last=null;previousPlayer=null;
 }
 function update(now,{active,boss,player,velocity={x:0,y:0},shield=false}) {
  const dt=last===null?0:Math.max(0,now-last);last=now;
  if(state.playerHP<=0){state.phase='defeat';state.bullets=[];return;}
  if(state.bossHP<=0){state.phase='victory';state.bullets=[];return;}
  if(!active||!boss||dt>.5) {
   state.phase='waiting';state.target=null;state.bullets=[];previousPlayer=null;return;
  }
  const prior=previousPlayer??player;
  state.bullets=state.bullets.filter(b=>{
   // Sweep in player-relative space to catch both bullet and player motion.
   const ax=b.x-prior.x,ay=b.y-prior.y;
   b.x+=b.vx*dt;b.y+=b.vy*dt;
   const dx=b.x-player.x-ax,dy=b.y-player.y-ay;
   const u=Math.max(0,Math.min(1,-(ax*dx+ay*dy)/(dx*dx+dy*dy||1)));
   if(Math.hypot(ax+u*dx,ay+u*dy)<=player.radius+b.radius) {
    if(shield){state.blocked++;state.bossHP=Math.max(0,state.bossHP-1);}else state.playerHP=Math.max(0,state.playerHP-25);
    return false;
   }
   const alive=b.x>=0&&b.x<=914.4&&b.y>=0&&b.y<=508&&now-b.born<5;
   if(!alive)state.bossHP=Math.max(0,state.bossHP-1); // successful dodge counters, as in the virtual boss
   return alive;
  });
  previousPlayer={...player};
  if(state.playerHP<=0){state.phase='defeat';state.bullets=[];return;}
  if(state.bossHP<=0){state.phase='victory';state.bullets=[];return;}
  if(state.phase==='waiting'||(state.phase==='recover'&&now-phaseAt>=cooldown)) {
   const horizon=Math.min(lead,warning+Math.hypot(player.x-boss.x,player.y-boss.y)/speed);
   state.target={x:Math.max(player.radius,Math.min(914.4-player.radius,player.x+velocity.x*horizon)),
                 y:Math.max(player.radius,Math.min(508-player.radius,player.y+velocity.y*horizon))};
   state.phase='warning';phaseAt=now;
  }else if(state.phase==='warning'&&now-phaseAt>=warning) {
   const dx=state.target.x-boss.x,dy=state.target.y-boss.y,d=Math.hypot(dx,dy)||1;
   state.bullets.push({x:boss.x,y:boss.y,vx:dx/d*speed,vy:dy/d*speed,radius:7,born:now});
   state.phase='recover';phaseAt=now;
  }
 }
 return {state,reset,update};
}
