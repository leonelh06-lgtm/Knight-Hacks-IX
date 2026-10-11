import test from 'node:test';
import assert from 'node:assert/strict';
import { createL2 } from './l2.mjs';

const room = { minX: -8.89, maxX: 8.89, minZ: -1, maxZ: 9 };
function game(options = {}) {
  const hero = { position: { x: 0, z: 0 } };
  const ctl = createL2({ room, hero, HERO_R: 0.3, ...options });
  ctl.start(0);
  return { ctl, hero, s: ctl.state };
}
function tick(ctl, from, to) {
  for (let t = from + 1 / 60; t <= to + 1e-8; t += 1 / 60) ctl.update(t);
}
test('touching either hunter kills immediately, then retries this level', () => {
  for (const index of [0, 1]) {
    const { ctl, hero, s } = game();
    const p = s.hunters?.[index]?.position ?? s.anchors[index ? 'B' : 'A'];
    Object.assign(hero.position, p);
    ctl.update(1 / 60);
    assert.equal(s.phase, 'DEAD');
    assert.equal(s.deaths, 1);
    tick(ctl, 1 / 60, 2);
    assert.equal(s.phase, 'PLAYING');
    assert.equal(s.deaths, 1);
    assert.ok(s.elapsed < 1);
  }
});
test('a stationary player gets caught by moving hunters', () => {
  const { ctl, s } = game();
  const initial = s.hunters?.map(h => ({ ...h.position }));
  tick(ctl, 0, 1.5);
  assert.ok(s.hunters?.every((h, i) => Math.hypot(h.position.x - initial[i].x, h.position.z - initial[i].z) > 0.1));
  for (let t = 1.5; t < 15 && s.phase === 'PLAYING'; t += 1 / 60) ctl.update(t);
  assert.equal(s.phase, 'DEAD');
});
test('twenty seconds of survival clears, never early', () => {
  const { ctl, s } = game({ SPEED_START: 0, SPEED_END: 0, LUNGE_SPEED: 0 });
  tick(ctl, 0, 19.9);
  assert.equal(s.phase, 'PLAYING');
  tick(ctl, 19.9, 20);
  assert.equal(s.phase, 'CLEARED');
  assert.equal(s.remaining, 0);
});
test('swept contact catches crossing an enemy between frames', () => {
  const { ctl, hero, s } = game({ SPEED_START: 0, SPEED_END: 0, LUNGE_SPEED: 0 });
  assert.ok(s.hunters, 'moving hunters must be available');
  const p = s.hunters[0].position;
  hero.position.z = p.z - 2;
  ctl.update(1 / 60);
  hero.position.x = p.x - 1.5;
  ctl.update(2 / 60);
  hero.position.z = p.z;
  ctl.update(3 / 60);
  assert.equal(s.phase, 'PLAYING');
  hero.position.x = p.x + 1.5;
  ctl.update(4 / 60);
  assert.equal(s.phase, 'DEAD');
});
test('death wins over a simultaneous survival timeout', () => {
  const { ctl, hero, s } = game({ SPEED_START: 0, SPEED_END: 0, LUNGE_SPEED: 0 });
  tick(ctl, 0, 19.99);
  Object.assign(hero.position, s.hunters?.[0]?.position ?? s.anchors.A);
  ctl.update(20);
  assert.equal(s.phase, 'DEAD');
});
test('lunges warn first, lock their direction, and recover', () => {
  const { ctl, hero, s } = game({ SPEED_START: 0, SPEED_END: 0, LUNGE_SPEED: 0 });
  tick(ctl, 0, 3.7);
  const hunter = s.hunters[0];
  assert.equal(hunter.mode, 'warning');
  const direction = { ...hunter.direction };
  hero.position.x += 0.4;
  tick(ctl, 3.7, 3.8);
  assert.deepEqual(hunter.direction, direction);
  tick(ctl, 3.8, 4.05);
  assert.equal(hunter.mode, 'lunge');
  tick(ctl, 4.05, 4.4);
  assert.equal(hunter.mode, 'recover');
});
test('a suspended tab does not skip the survival countdown', () => {
  const { ctl, s } = game();
  ctl.update(60);
  assert.equal(s.phase, 'PLAYING');
  assert.ok(s.remaining > 19.9);
});
