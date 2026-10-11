// Run the real page script and modules with only browser I/O stubbed.
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import assert from 'node:assert/strict';
import { createFight } from './fight.js';
import { DodgePredictor } from './predictor.mjs';
import { makeAdaptive, makeRandomShift, withEscapeCheck } from './aim.mjs';
import { LEVELS } from './levels.mjs';
import { createMaze, step as mazeStep } from './maze.mjs';
import { drawMazeFlat, drawMazeHUD, drawClearScreen } from './maze_view.mjs';
import { createL2, floorFromRoom } from './l2.mjs';
import { drawHunters, drawHuntHUD } from './l2_view.mjs';
function page() {
  let time = 0, next; const handlers = {};
  const ctx = new Proxy({ createRadialGradient: () => ({ addColorStop() {} }) }, {
    get: (o, k) => o[k] ?? (() => {}), set: (o, k, v) => (o[k] = v, true),
  });
  const sandbox = { createFight, DodgePredictor, makeAdaptive, makeRandomShift, withEscapeCheck,
    LEVELS, createMaze, mazeStep, drawMazeFlat, drawMazeHUD, drawClearScreen, createL2, floorFromRoom,
    drawHunters, drawHuntHUD, console, performance: { now: () => time * 1000 },
    window: { innerWidth: 1280, innerHeight: 720 }, document: { getElementById: () => ({ getContext: () => ctx }) },
    Image: class {}, WebSocket: class { addEventListener() {} },
    addEventListener: (name, fn) => handlers[name] = fn, requestAnimationFrame: fn => next = fn };
  vm.createContext(sandbox);
  const read = code => vm.runInContext(code, sandbox);
  const source = fs.readFileSync(new URL('./debug.html', import.meta.url), 'utf8').split('<script type="module">')[1].split('</script>')[0].replace(/^import .*;\r?\n/gm, '');
  read(source);
  return { read, key: code => handlers.keydown({ code, preventDefault() {} }),
    frame: t => { time = t; next(); }, resize: () => handlers.resize() };
}
test('maze clear enters the hunt, contact retries, and survival advances', () => {
  const p = page();
  p.read('mazeState.hero = {...mazeState.goal}'); p.frame(0.1); p.frame(2.7); p.frame(2.8);
  assert.equal(p.read('levelIndex'), 1);
  assert.equal(p.read('l2State.state.phase'), 'PLAYING');
  p.key('KeyH'); p.key('KeyO'); p.frame(2.9);
  p.read('Object.assign(hero.position, l2State.state.hunters[0].position)'); p.frame(3);
  assert.equal(p.read('l2State.state.phase'), 'DEAD');
  p.frame(4.7); assert.equal(p.read('levelIndex'), 1);
  assert.equal(p.read('l2State.state.phase'), 'PLAYING');
  p.read("l2State = createL2({room: cfg.room, hero, HERO_R, SPEED_START: 0, SPEED_END: 0, LUNGE_SPEED: 0}); l2State.start(4.7)");
  for (let i = 1; i <= 1200; i++) p.frame(4.7 + i / 60);
  assert.equal(p.read('l2State.state.phase'), 'CLEARED');
  p.frame(27.3); p.frame(27.4);
  assert.equal(p.read('levelIndex'), 2);
});
test('shortcut, resize, and calibration exit leave level 2 running', () => {
  const p = page(); p.key('Digit2'); p.frame(0.1);
  p.resize(); p.frame(0.2); assert.equal(p.read('l2State.state.phase'), 'PLAYING');
  p.key('KeyT'); p.frame(0.3); assert.equal(p.read('l2Calibrating'), true);
  p.key('KeyT'); p.frame(0.4); assert.equal(p.read('l2State.state.phase'), 'PLAYING');
  p.key('KeyR'); p.frame(0.5); assert.equal(p.read('l2State.state.phase'), 'PLAYING');
});
test('resizing after leaving level 2 does not teleport the boss-level hero', () => {
  const p = page(); p.key('Digit2'); p.frame(0.1); p.key('Digit3'); p.frame(0.2);
  p.read('hero.position.x = 3; hero.position.z = 6'); p.resize();
  assert.equal(p.read('hero.position.x'), 3);
  assert.equal(p.read('hero.position.z'), 6);
});
