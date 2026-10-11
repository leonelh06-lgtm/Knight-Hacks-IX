import { drawLennyEyes } from './lenny.mjs';
import { LESSONS } from './intro.mjs';
const clamp = x => Math.max(0,Math.min(1,x));
const ease = x => { x=clamp(x); return x*x*(3-2*x); };
const mix = (a,b,t) => a+(b-a)*t;
export function cinematicBeat(t) {
 if(t<6) return {speaker:'',text:'',alpha:0,bottom:true};
 if(t<10.5) return {speaker:'LENNY',text:'Where am I? What is this place?',alpha:Math.min(ease((t-6)/.8),ease((10.5-t)/.6)),bottom:true};
 if(t<14.1) return {speaker:'LENNY',text:'Who are you?',alpha:Math.min(ease((t-10.5)/.7),ease((14.1-t)/.6)),bottom:false};
 if(t<18.5) return {speaker:'THE LIGHT',text:'Follow my lead. I will guide you.',alpha:Math.min(ease((t-14.1)/.9),ease((18.5-t)/.7)),bottom:false};
 return {speaker:'',text:'',alpha:0,bottom:false};
}
function drawLenny(ctx,img,x,y,size,time,waking) {
 const rise=waking?ease((time-2.4)/3):1;
 const breath= Math.sin(time*1.7)*.013;
 ctx.save();ctx.translate(x,y+(1-rise)*12);
 ctx.rotate(waking?mix(-.18,0,rise)+(time>9?Math.sin(time)*.035:0):0);
 ctx.scale(1+breath,mix(.73,1,rise)+breath);
 ctx.shadowColor='#75a88a';ctx.shadowBlur=3;
 if(img.complete&&img.naturalWidth>0){
  const height=size*img.naturalHeight/img.naturalWidth;
  ctx.filter=`hue-rotate(22deg) saturate(1.25) brightness(${mix(.6,.92,rise)}) contrast(1.06)`;
  ctx.drawImage(img,-size/2,-height/2,size,height);ctx.filter='none';
  drawLennyEyes(ctx,size,height,waking?time:performance.now()/1000,waking);
 } else {ctx.fillStyle='#bfe28d';ctx.beginPath();ctx.ellipse(0,0,size*.32,size*.43,0,0,Math.PI*2);ctx.fill();}
 ctx.restore();
}
export function drawIntro(ctx,canvas,state,{sprite,heroX,heroY,heroSize=60}) {
 const w=canvas.width,h=canvas.height,t=state.time,cinema=state.phase==='cinematic';
 ctx.save();
 if(cinema){
  const reveal=ease((t-17.8)/3.2),travel=ease((t-18.2)/2.8);
  const x=mix(w/2,heroX,travel),y=mix(h*.52,heroY,travel);
  const size=mix(Math.min(155,w*.23,h*.25),heroSize,travel);
  const radius=mix(size*.63+ease((t-1.2)/4)*size*.2,Math.hypot(w,h)*1.1,reveal);
  // The room was drawn underneath; a radial scrim opens a soft spotlight over it.
  const darkness=ctx.createRadialGradient(x,y,radius*.48,x,y,radius);
  darkness.addColorStop(0,`rgba(0,0,0,${mix(1-ease((t-1.2)/2)*.1,0,ease(reveal*2))})`);
  darkness.addColorStop(1,`rgba(0,0,0,${1-ease((reveal-.65)/.35)})`);
  ctx.fillStyle=darkness;ctx.fillRect(0,0,w,h);
  if(t>1.2){
   const halo=ctx.createRadialGradient(x,y,0,x,y,radius);
   halo.addColorStop(0,`rgba(177,192,127,${.26*(1-reveal)})`);halo.addColorStop(.65,`rgba(149,167,106,${.15*(1-reveal)})`);halo.addColorStop(1,'rgba(0,0,0,0)');
   ctx.fillStyle=halo;ctx.fillRect(0,0,w,h);
   ctx.globalAlpha=ease((t-1.5)/1.8);drawLenny(ctx,sprite,x,y,size,t,true);ctx.globalAlpha=1;
  }

  const bar=h*.065*(1-reveal);ctx.fillStyle='#000';ctx.fillRect(0,0,w,bar);ctx.fillRect(0,h-bar,w,bar);
  if(t>2&&t<18){
   ctx.fillStyle='#e7e9c0';
   for(let i=0;i<16;i++){ctx.globalAlpha=.06*(1-reveal)*(1+Math.sin(t*.7+i));const a=i*2.399+t*.015;const r=radius*(.2+(i%5)*.13);ctx.beginPath();ctx.arc(x+Math.cos(a)*r,y+Math.sin(a)*r,1,0,7);ctx.fill();}
   ctx.globalAlpha=1;
  }
 }else{
  ctx.fillStyle='rgba(3,14,9,.38)';ctx.fillRect(0,0,w,h);
  const pulse=1+Math.sin(performance.now()/600)*.06;
  ctx.strokeStyle='#d0ec9a';ctx.lineWidth=2;ctx.shadowColor='#d0ec9a';ctx.shadowBlur=20;
  ctx.beginPath();ctx.arc(heroX,heroY,43*pulse,0,Math.PI*2);ctx.stroke();ctx.shadowBlur=0;
  const lesson=LESSONS[Math.min(state.step,4)], drift=Math.sin(clamp(state.hold/.6)*Math.PI)*16;
  drawLenny(ctx,sprite,heroX+lesson.x*drift,heroY+lesson.y*drift,heroSize,0,false);
 }
 ctx.restore();
}
function icon(step){
 const open=step===0, fist=step===1, pinch=step===2||step===3;
 const fingers=step===3?'M24 42Q39 33 57 38Q65 39 60 45 M27 38V18Q29 10 34 16V36 M39 34V10Q44 5 47 13V35 M51 35V20Q55 15 58 23V37':open?'M24 42V17Q24 10 29 12V37 M34 35V9Q35 3 40 8V36 M45 36V13Q48 7 51 14V40 M56 41V23Q61 18 62 26V52':fist?'M24 38V31Q27 24 33 30V37 M34 35V28Q39 23 44 30V37 M45 38V32Q51 26 55 34V43 M56 45V40Q61 35 63 42V54':'M25 42Q18 17 29 17L35 36 M38 36V12Q43 6 46 14V38 M50 39V19Q55 12 58 21V44 M60 45V33';
 return `<svg viewBox="0 0 80 90" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M24 42Q13 31 11 41L21 61Q25 76 39 78Q61 79 63 54"/><path d="${fingers}"/>${pinch?`<circle cx="${step===3?57:25}" cy="${step===3?40:34}" r="8" stroke="#8fa56d" stroke-dasharray="3 3"/>`: ''}<path d="M31 86H54" stroke="#75905b"/></svg>`;
}
export function bindIntroUI(document,controller,onFinish,onReplay){
 const ids=['skip-intro','replay-intro','intro-caption','intro-speaker','intro-line','lesson-card','lesson-title','lesson-action','lesson-detail','lesson-key','lesson-icon','lesson-progress','lesson-feedback','lesson-steps','lesson-count'];
 const el=Object.fromEntries(ids.map(id=>[id,document.getElementById(id)]));
 el['skip-intro'].addEventListener('click',()=>{controller.skip();if(controller.state.phase==='done')onFinish();});
 el['replay-intro'].addEventListener('click',onReplay);
 let lastStep=-1,lastPhase='',lastCaption='';
 function update({gestureFresh=false}={}){
  const s=controller.state,cinema=s.phase==='cinematic',done=s.phase==='done';
  el['skip-intro'].hidden=done;el['replay-intro'].hidden=!done;
  el['skip-intro'].textContent=cinema?'Skip intro  ·  Esc':'Skip tutorial  ·  Esc';
  el['intro-caption'].hidden=!cinema;el['lesson-card'].hidden=cinema;
  el['lesson-card'].style.opacity=done?'0':'1';
  el['lesson-card'].style.visibility=done?'hidden':'visible';
  el['lesson-card'].style.pointerEvents=done?'none':'auto';
  if(cinema){const beat=cinematicBeat(s.time);if(beat.text!==lastCaption){el['intro-speaker'].textContent=beat.speaker;el['intro-line'].textContent=beat.text;lastCaption=beat.text;}el['intro-caption'].className=beat.bottom?'bottom':'';el['intro-caption'].style.opacity=beat.alpha;}
  if(!cinema&&!done){
   if(lastStep!==s.step||lastPhase!==s.phase){
    const lesson=LESSONS[Math.min(s.step,4)];
    el['lesson-title'].textContent=lesson.title;
    el['lesson-action'].textContent=lesson.action;
    el['lesson-detail'].textContent=lesson.detail;
    el['lesson-key'].textContent=lesson.key;
    el['lesson-icon'].innerHTML=icon(s.step);
    el['lesson-count'].textContent=`FOLLOW MY LEAD / ${s.step+1} OF 5 · ${lesson.dir}`;
    el['lesson-steps'].innerHTML=LESSONS.map((_,i)=>`<span class="${i<s.step?'complete':i===s.step?'current':''}"></span>`).join('');
   }
   el['lesson-progress'].style.width=`${Math.min(100,s.hold/.6*100)}%`;
   el['lesson-feedback'].textContent=s.feedback?'That’s it. You’re doing great.':s.hold>0?'Hold gently…':gestureFresh?'Show the gesture, or use the keyboard.':'Waiting for your hand · keyboard works too';
  }
  lastStep=s.step;lastPhase=s.phase;
 }
 return {update};
}
