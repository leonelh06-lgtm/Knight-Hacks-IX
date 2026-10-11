// Run: node l2.sim.mjs. Deterministic movement bots are tuning aids, not human playtests.
import assert from 'node:assert/strict';
import { createL2 } from './l2.mjs';
let cleared = 0, runs = 0;
for (const aspect of [0.94, 16/9, 21/9]) for (const clockwise of [-1, 1]) {
  const hero = { position: { x: 0, z: 0 } };
  const ctl = createL2({ room: { minX: -5*aspect, maxX: 5*aspect, minZ: -1, maxZ: 9 }, hero, HERO_R: 0.42 });
  ctl.start(0); const s = ctl.state, floor = s.floor;
  let vel = { x: 0, z: 0 }, bestAngle = 0;
  for (let frame = 1; frame <= 1201 && s.phase === 'PLAYING'; frame++) {
    // Choose a route every 150ms, preserving realistic reaction delay.
    if (frame % 9 === 1) {
      let best = -Infinity;
      for (let i = 0; i < 32; i++) {
        const a = i * Math.PI / 16, vx = Math.cos(a)*3, vz = Math.sin(a)*3;
        const px = hero.position.x + vx*0.65, pz = hero.position.z + vz*0.65;
        const edge = Math.hypot((px-floor.cx)/(floor.rx-0.5), (pz-floor.cz)/(floor.rz-0.5));
        let score = Math.min(...s.hunters.map(h => {
          const look = h.mode === 'lunge' ? 0.3 : 0.12;
          return Math.hypot(px-h.position.x-h.direction.x*look, pz-h.position.z-h.direction.z*look);
        }));
        score -= Math.max(0, edge-0.85)*12;
        score += Math.cos(a-bestAngle)*0.2;
        score += clockwise*((hero.position.x-floor.cx)*vz-(hero.position.z-floor.cz)*vx)*0.02;
        if(score>best) { best=score; vel={x:vx,z:vz}; }
      }
      bestAngle=Math.atan2(vel.z,vel.x);
    }
    hero.position.x += vel.x/60; hero.position.z += vel.z/60;
    const dx=(hero.position.x-floor.cx)/(floor.rx-0.42), dz=(hero.position.z-floor.cz)/(floor.rz-0.42), d=Math.hypot(dx,dz);
    if(d>1) { hero.position.x=floor.cx+dx/d*(floor.rx-0.42); hero.position.z=floor.cz+dz/d*(floor.rz-0.42); }
    ctl.update(frame/60);
    for(const hunter of s.hunters) {
      const p=hunter.position;
      assert.ok(Math.hypot((p.x-floor.cx)/(floor.rx-hunter.radius),(p.z-floor.cz)/(floor.rz-hunter.radius)) <= 1.00001, 'hunter escaped the map');
    }
  }
  runs++; if(s.phase==='CLEARED') cleared++;
  console.log(`aspect=${aspect.toFixed(2)} direction=${clockwise}: ${s.phase} at ${s.elapsed.toFixed(2)}s`);
}
assert.ok(cleared > 0, 'At least one delayed evasive route must survive with default tuning');
console.log(`Evasive simulations: ${cleared}/${runs} survived. These are synthetic bots, not human difficulty ratings.`);
