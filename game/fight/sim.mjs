import { createFight } from './fight.js';
import { DodgePredictor } from './predictor.mjs';
import { makeAdaptive, makeRandomShift } from './aim.mjs';

const cfg = { position: { x: 0, z: 0 }, halfAngle: 0.35, range: 7, counter: 0.5,
              room: { minX: -5, maxX: 5, minZ: -1, maxZ: 9 } };
const HOME = { x: 0, z: 5 }, SPEED = 3, REACT = 0.25, DODGE = 2.6, DT = 1 / 60;

function rng(seed) {                             // mulberry32, so runs are repeatable
  return () => { seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
function step(p, to, d) {
  const dx = to.x - p.x, dz = to.z - p.z, len = Math.hypot(dx, dz);
  if (len <= d) { p.x = to.x; p.z = to.z; } else { p.x += dx / len * d; p.z += dz / len * d; }
}
const policies = {                               // 'A' = the predictor's PLUS side
  alwaysA: () => 'A',
  alternate: (k) => (k % 2 ? 'A' : 'B'),
  random: (k, r) => (r() < 0.5 ? 'A' : 'B'),
  habitThenSwitch: (k) => (k < 12 ? 'A' : 'B'),
};

function run(policy, adaptive, attacks = 40, seed = 1) {
  const rand = rng(seed), hero = { position: { ...HOME } }, predictor = new DodgePredictor();
  const results = [];
  const ctl = createFight(cfg, hero, {
    chooseAim: adaptive ? makeAdaptive(predictor, { rand }) : makeRandomShift(rand),
    onResolve: (e) => {
      predictor.observe({ x: e.p0.x, y: e.p0.z }, { x: e.p1.x, y: e.p1.z }, { x: e.aim.x, y: e.aim.z });
      results.push(e.hit);
    },
  });
  let t = 0, target = null, decidedFor = -1, warnStart = 0;
  ctl.start(t);
  for (let i = 0; i < attacks * 400 && results.length < attacks; i++) {
    t += DT;
    const s = ctl.state; s.playerHP = 100; s.bossHP = 3;   // keep the fight going
    if (s.phase === 'warning') {
      if (decidedFor !== results.length) {
        decidedFor = results.length; warnStart = t;
        const sign = policy(results.length, rand) === 'A' ? 1 : -1;
        target = { x: hero.position.x + (-s.aim.z) * sign * DODGE, z: hero.position.z + s.aim.x * sign * DODGE };
      }
      if (t - warnStart >= REACT) step(hero.position, target, SPEED * DT);
    } else step(hero.position, HOME, SPEED * DT);
    ctl.update(t);
  }
  return results;
}
const pct = (a) => (100 * a.filter(Boolean).length / a.length).toFixed(0) + '%';
for (const [name, pol] of Object.entries(policies))
  for (const adaptive of [false, true]) {
    const r = run(pol, adaptive);
    console.log(name.padEnd(16), (adaptive ? 'adaptive' : 'random-shift').padEnd(13),
                'hits', pct(r), '| after 5 warm-up attacks', pct(r.slice(5)));
  }
