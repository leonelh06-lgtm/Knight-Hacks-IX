// Run the real page script and modules with only browser I/O stubbed.
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import assert from 'node:assert/strict';
import { createFight } from './fight.js';
import { DodgePredictor } from './predictor.mjs';
import { makeAdaptive, makeRandomShift, withEscapeCheck } from './aim.mjs';
import { LEVELS } from './levels.mjs';
import { createRoverClient } from './rover_client.mjs';
import { createRoverBoss, toBoardPlayer, roverEligible } from './rover_boss.mjs';
import { randomUUID } from 'node:crypto';
import { createMaze, step as mazeStep } from './maze.mjs';
import { drawMazeFlat, drawMazeHUD, drawClearScreen } from './maze_view.mjs';
import { createL2, floorFromRoom } from './l2.mjs';
import { drawHunters, drawHuntHUD } from './l2_view.mjs';
function page(calibration = null) {
  let time = 0, next; const handlers = {};
  const ctx = new Proxy({ createRadialGradient: () => ({ addColorStop() {} }) }, {
    get: (o, k) => o[k] ?? (() => {}), set: (o, k, v) => (o[k] = v, true),
  });
  const sandbox = { createFight, DodgePredictor, makeAdaptive, makeRandomShift, withEscapeCheck,
    LEVELS, createRoverClient, createRoverBoss, toBoardPlayer, roverEligible, createMaze, mazeStep, drawMazeFlat, drawMazeHUD, drawClearScreen, createL2, floorFromRoom,
    drawHunters, drawHuntHUD, console, crypto: {randomUUID}, URLSearchParams, location:{search:''}, fetch:()=>({ok:!!calibration,json:()=>calibration}), performance: { now: () => time * 1000 },
    window: { innerWidth: 1280, innerHeight: 720 }, document: { hidden:false, addEventListener() {}, getElementById: () => ({ getContext: () => ctx }) },
    Image: class {}, WebSocket: class {
      readyState=1; sent=[]; handlers={};
      addEventListener(name,fn) { (this.handlers[name]??=[]).push(fn); }
      removeEventListener(name,fn) { this.handlers[name]=this.handlers[name]?.filter(x=>x!==fn)??[]; }
      send(raw) { this.sent.push(JSON.parse(raw)); }
      emit(message) { for(const fn of this.handlers.message??[]) fn({data:JSON.stringify(message)}); }
    },
    addEventListener: (name, fn) => handlers[name] = fn, requestAnimationFrame: fn => next = fn };
  vm.createContext(sandbox);
  const read = code => vm.runInContext(code, sandbox);
  const source = fs.readFileSync(new URL('./debug.html', import.meta.url), 'utf8').split('<script type="module">')[1].split('</script>')[0].replace(/^import .*;\r?\n/gm, '').replace('await fetch(', 'fetch(').replace('await response.json()', 'response.json()');
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


test('hunter and ruins stay virtual; only fourth level prepares the physical rover', () => {
  const calibration={verified:true,calibration_id:'c',projection_size:[1280,720],arena:{x_mm:0,y_mm:0,width_mm:914.4,height_mm:508}};
  const p=page(calibration);
  p.key('Digit2');p.frame(.1);assert.equal(p.read('isPhysicalBoss()'),false);
  p.key('Digit3');p.frame(.2);assert.equal(p.read('isPhysicalBoss()'),false);
  p.key('Digit4');p.frame(.3);assert.equal(p.read('isPhysicalBoss()'),true);
  assert.equal(p.read('physicalState.phase'),'waiting');
  assert.equal(p.read('LEVELS[levelIndex].id'),'boss-arena');
  p.read("ws.emit({type:'game_claimed',session_id:roverSession})");p.frame(.4);
  assert.equal(p.read('ws.sent.at(-1).active'),true);
  assert.equal(p.read('physicalState.phase'),'waiting'); // readiness never arms motors
  p.key('KeyP');p.frame(.5);assert.equal(p.read('ws.sent.at(-1).active'),false);
  p.key('Digit2');p.frame(.6);assert.equal(p.read('isPhysicalBoss()'),false);
});
