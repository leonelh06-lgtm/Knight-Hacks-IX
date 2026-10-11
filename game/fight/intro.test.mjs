import test from 'node:test';
import assert from 'node:assert/strict';
import { createIntro } from './intro.mjs';
function advance(c, seconds, input = {}) { for(let t=0;t<seconds;t+=0.05) c.update(0.05,input); }
const gesture = (vx,vy,status='moving') => ({gestureFresh:true, gesture:{vx,vy,status,active:!!(vx||vy)}});
test('story reaches tutorial without starting gameplay',()=>{
 const c=createIntro(); assert.equal(c.state.phase,'cinematic'); advance(c,22);
 assert.equal(c.state.phase,'tutorial'); assert.equal(c.state.step,0);
});
test('wrong direction and stale packets cannot pass a movement lesson',()=>{
 const c=createIntro(); c.skip(); advance(c,2,gesture(0,1)); assert.equal(c.state.step,0);
 advance(c,2,{...gesture(0,-1),gestureFresh:false}); assert.equal(c.state.step,0);
 advance(c,1,gesture(0,-1)); assert.equal(c.state.step,1);
});
test('all four gestures and relaxed hand start gameplay immediately',()=>{
 const c=createIntro(); c.skip();
 for(const [x,y] of [[0,-1],[0,1],[-1,0],[1,0]]) advance(c,1,gesture(x,y));
 assert.equal(c.state.step,4);
 advance(c,1,{gestureFresh:false,gesture:{vx:0,vy:0,status:'No hand detected'}});
 assert.equal(c.state.phase,'tutorial');
 advance(c,1,gesture(0,0,'Relaxed / unclear hand: stopped'));
 assert.equal(c.state.phase,'done');
});
test('keyboard fallback works even when a neutral gesture stream is connected',()=>{
 const c=createIntro(); c.skip();
 for(const code of ['KeyW','KeyS','KeyA','KeyD']) advance(c,1,{...gesture(0,0,'Relaxed'),keys:{[code]:true}});
 advance(c,1,{keys:{}}); assert.equal(c.state.phase,'done');
});
test('skip and replay are explicit and deterministic',()=>{
 const c=createIntro(); c.skip(); assert.equal(c.state.phase,'tutorial');
 c.skip(); assert.equal(c.state.phase,'done'); c.replay();
 assert.equal(c.state.phase,'cinematic'); assert.equal(c.state.time,0); assert.equal(c.state.step,0);
});

test('keyboard tutorial finishes on release even with an active camera gesture',()=>{
 const c=createIntro(); c.skip();
 for(const code of ['KeyW','KeyS','KeyA','KeyD']) advance(c,1,{...gesture(0,-1),keys:{[code]:true}});
 advance(c,1,{...gesture(0,-1),keys:{}});
 assert.equal(c.state.phase,'done');
});
