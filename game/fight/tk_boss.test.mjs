import test from 'node:test';
import assert from 'node:assert/strict';
import { createTKBoss } from './tk_boss.mjs';

function arena() {
  const hero = { position: { x: 0, z: 5 } };
  const boss = createTKBoss({ hero, room: { minX: -8, maxX: 8, minZ: -1, maxZ: 9 } });
  boss.start(0);
  let time = 0;
  const stepTo = to => {
    while (time < to - 1e-8) {
      const dt = Math.min(.05, to - time);
      time += dt; boss.update(time, dt);
    }
  };
  return { hero, boss, state: boss.state, stepTo };
}

test('awakening locks the attack at Lenny for one second, then fires once', () => {
  const { hero, boss, state, stepTo } = arena();
  assert.equal(state.message, 'BOSS AWAKENED');
  assert.equal(state.phase, 'warning');
  const aim = { ...state.aim }, origin = { ...state.position };
  hero.position.x = 4;
  stepTo(0.9);
  assert.deepEqual(state.aim, aim);
  assert.deepEqual(state.position, origin);
  stepTo(1);
  assert.equal(state.phase, 'laser');
  assert.equal(state.hits, 0);
  assert.equal(state.message, 'DODGED!');
  stepTo(1.2);
  assert.equal(state.hits, 0);
});

test('laser hits at most once and three hits defeat Lenny', () => {
  const { hero, boss, state, stepTo } = arena();
  for (let i = 0; i < 3; i++) {
    hero.position.x = state.position.x;
    hero.position.z = state.position.z + 3;
    stepTo(i * 3.45 + 1);
    assert.equal(state.hits, i + 1);
    if (i < 2) {
      stepTo(i * 3.45 + 1.45);
      assert.equal(state.phase, 'recover');
      stepTo(i * 3.45 + 3.45);
      assert.equal(state.phase, 'warning');
    }
  }
  assert.equal(state.phase, 'defeat');
  boss.update(20, 0.05);
  assert.equal(state.hits, 3);
});

test('TK pursues during recovery and surviving thirty seconds wins', () => {
  const { hero, boss, state, stepTo } = arena();
  hero.position.x = 6;
  stepTo(1);
  stepTo(1.45);
  assert.equal(state.phase, 'recover');
  const before = { ...state.position };
  stepTo(1.5);
  assert.ok(Math.hypot(state.position.x - before.x, state.position.z - before.z) > 0);
  assert.equal(state.phase, 'recover');
  stepTo(3.44);
  assert.equal(state.phase, 'recover');
  stepTo(3.45);
  assert.equal(state.phase, 'warning');
  hero.position.x = 100;
  stepTo(30);
  assert.equal(state.phase, 'victory');
  assert.equal(state.remaining, 0);
});

test('a suspended tab cannot skip the thirty-second fight', () => {
  const { boss, state } = arena();
  boss.update(60, 0.05);
  assert.equal(state.phase, 'warning');
  assert.ok(state.remaining > 29.9);
});
