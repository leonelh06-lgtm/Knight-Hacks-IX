import test from 'node:test';
import assert from 'node:assert/strict';
import * as projectiles from './rover_boss.mjs';

test('physical shots lead a moving player and originate at the live robot pose', () => {
  assert.equal(typeof projectiles.createRoverProjectiles, 'function');
  const c = projectiles.createRoverProjectiles({warning: .5, speed: 300});
  c.update(0, {active:true, boss:{x:100,y:200}, player:{x:500,y:200,radius:15}, velocity:{x:0,y:100}});
  assert.ok(c.state.target.y > 200);
  c.update(.5, {active:true, boss:{x:120,y:200}, player:{x:500,y:250,radius:15}, velocity:{x:0,y:100}});
  assert.equal(c.state.bullets.length, 1);
  assert.equal(c.state.bullets[0].x,120);
  assert.equal(c.state.bullets[0].y,200);
  assert.ok(c.state.bullets[0].vy > 0);
});

test('swept projectile collision hits once even across a long frame', () => {
  assert.equal(typeof projectiles.createRoverProjectiles, 'function');
  const c = projectiles.createRoverProjectiles({warning:0, speed:1000});
  const input={active:true,boss:{x:100,y:200},player:{x:200,y:200,radius:15},velocity:{x:0,y:0}};
  c.update(0,input); c.update(.01,input); c.update(.21,input);
  assert.equal(c.state.playerHP,75);
  assert.equal(c.state.bullets.length,0);
  c.update(.22,input); assert.equal(c.state.playerHP,75);
});

test('tracking loss clears shots and restarts a full warning on reacquisition', () => {
  assert.equal(typeof projectiles.createRoverProjectiles, 'function');
  const c = projectiles.createRoverProjectiles({warning:.5});
  const input={active:true,boss:{x:100,y:200},player:{x:600,y:200,radius:15},velocity:{x:0,y:0}};
  c.update(0,input);c.update(.5,input);assert.equal(c.state.bullets.length,1);
  c.update(.6,{...input,active:false});assert.equal(c.state.bullets.length,0);
  c.update(10,input);assert.equal(c.state.bullets.length,0);
  c.update(10.4,input);assert.equal(c.state.bullets.length,0);
});

test('shield blocks bullets and reset restores player health', () => {
  assert.equal(typeof projectiles.createRoverProjectiles, 'function');
  const c=projectiles.createRoverProjectiles({warning:0,speed:1000});
  const input={active:true,boss:{x:100,y:200},player:{x:200,y:200,radius:15},velocity:{x:0,y:0},shield:true};
  c.update(0,input);c.update(.01,input);c.update(.21,input);
  assert.equal(c.state.playerHP,100);assert.equal(c.state.bullets.length,0);
  c.reset();assert.equal(c.state.playerHP,100);assert.equal(c.state.phase,'waiting');
});

test('three defended attacks defeat the boss, and terminal updates cannot fire', () => {
  const c=projectiles.createRoverProjectiles({warning:0,speed:1000,cooldown:0});
  const input={active:true,boss:{x:100,y:200},player:{x:200,y:200,radius:15},velocity:{x:0,y:0},shield:true};
  c.update(0,input);
  for(let i=1;i<=8;i++)c.update(i*.1,input);
  assert.equal(c.state.phase,'victory');assert.equal(c.state.bossHP,0);
  c.update(1,input);assert.equal(c.state.bullets.length,0);
  c.reset();assert.equal(c.state.bossHP,3);
});
