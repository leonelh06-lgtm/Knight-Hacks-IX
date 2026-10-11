// Intro timing and tutorial recognition are independent of rendering and maze physics.
export const LESSONS = [
 {title:'Reach for the light',action:'Open your palm',detail:'Face your palm toward the camera. Open your fingers to move up.',key:'W',dir:'UP',x:0,y:-1},
 {title:'Find your footing',action:'Make a gentle fist',detail:'Close your fingers comfortably to move down.',key:'S',dir:'DOWN',x:0,y:1},
 {title:'A little to the left',action:'Pinch index finger + thumb',detail:'Keep your other fingers open. Touch index finger to thumb to move left.',key:'A',dir:'LEFT',x:-1,y:0},
 {title:'Now, the other way',action:'Pinch pinkie + thumb',detail:'Keep your other fingers open. Touch your little finger to thumb to move right.',key:'D',dir:'RIGHT',x:1,y:0},
 {title:'You set the pace',action:'Relax your hand',detail:'Let your fingers rest halfway open to stop. You do not need to hold a tight pose.',key:'Release keys',dir:'STOP',x:0,y:0},
];
export function createIntro() {
 const state={phase:'cinematic',time:0,step:0,hold:0,cooldown:0,control:'gesture',feedback:false};
 function replay(){Object.assign(state,{phase:'cinematic',time:0,step:0,hold:0,cooldown:0,control:'gesture',feedback:false});}
 function skip(){if(state.phase==='cinematic'){state.phase='tutorial';state.hold=0;}else state.phase='done';}
 function update(dt,input={}){
  dt=Math.max(0,Math.min(0.05,dt));
  if(state.phase==='cinematic'){state.time+=dt;if(state.time>=21)state.phase='tutorial';return;}
  if(state.phase!=='tutorial')return;
  if(state.cooldown>0){state.cooldown-=dt;return;}
  state.feedback=false;
  const k=input.keys??{},kx=Number(!!k.KeyD)-Number(!!k.KeyA),ky=Number(!!k.KeyS)-Number(!!k.KeyW);
  const pressed=!!(k.KeyA||k.KeyD||k.KeyW||k.KeyS);
  if(pressed)state.control='keyboard';
  else if(state.step<4&&input.gestureFresh&&input.gesture?.active)state.control='gesture';
  const lesson=LESSONS[state.step],g=input.gesture;
  let x=0,y=0,valid=false;
  if(pressed||(state.control==='keyboard'&&lesson.dir==='STOP')){x=kx;y=ky;valid=!pressed||!!(kx||ky);}
  else if(input.gestureFresh&&g){
   x=g.vx;y=g.vy;
   valid=lesson.dir==='STOP' ? /relaxed/i.test(g.status??'') : g.active===true;
  }
  let matches=false;
  if(valid&&Number.isFinite(x)&&Number.isFinite(y)){
   if(lesson.dir==='STOP')matches=Math.hypot(x,y)<0.12;
   else matches=x*lesson.x+y*lesson.y>0.35&&Math.abs(x*lesson.y-y*lesson.x)<0.3;
  }
  state.hold=matches?state.hold+dt:0;
  if(state.hold>=0.6-1e-8){state.step++;state.hold=0;state.feedback=true;state.cooldown=0.3;if(state.step===LESSONS.length)state.phase='done';}
 }
 return {state,update,skip,replay};
}
