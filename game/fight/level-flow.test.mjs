import { drawLennyEyes } from './lenny.mjs';
// Run the real page script and modules with only browser I/O stubbed.
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import assert from 'node:assert/strict';
import { createIntro } from './intro.mjs';
import { drawIntro, bindIntroUI } from './intro_view.mjs';
import { createFight } from './fight.js';
import { DodgePredictor } from './predictor.mjs';
import { makeAdaptive, makeRandomShift, withEscapeCheck } from './aim.mjs';
import { LEVELS } from './levels.mjs';
import { createRoverClient } from './rover_client.mjs';
import { createRoverBoss, toBoardPlayer, roverEligible, createRoverProjectiles } from './rover_boss.mjs';
import { randomUUID } from 'node:crypto';
import { createMaze, step as mazeStep } from './maze.mjs';
import { drawMazeFlat, drawMazeHUD, drawClearScreen } from './maze_view.mjs';
import { createL2, floorFromRoom } from './l2.mjs';
import { drawHunters, drawHuntHUD } from './l2_view.mjs';
import { createTKBoss } from './tk_boss.mjs';
import { drawTKArena, drawTKBoss, drawTKHUD } from './tk_view.mjs';
function page(calibration = null, search = '') {
  let time = 0, next; const handlers = {};
  const ctx = new Proxy({ createRadialGradient: () => ({ addColorStop() {} }) }, {
    get: (o, k) => o[k] ?? (() => {}), set: (o, k, v) => (o[k] = v, true),
  });
  const elements = new Map();
  const element = id => { if (!elements.has(id)) elements.set(id, { style: {}, addEventListener() {}, getContext: () => ctx }); return elements.get(id); };
  const sandbox = { drawLennyEyes, createIntro, drawIntro, bindIntroUI, createFight, DodgePredictor, makeAdaptive, makeRandomShift, withEscapeCheck,
    LEVELS, createRoverClient, createRoverBoss, toBoardPlayer, roverEligible, createRoverProjectiles, createMaze, mazeStep, drawMazeFlat, drawMazeHUD, drawClearScreen, createL2, floorFromRoom,
    drawHunters, drawHuntHUD, createTKBoss, drawTKArena, drawTKBoss, drawTKHUD, console, crypto: {randomUUID}, URLSearchParams, location:{search}, fetch:()=>({ok:!!calibration,json:()=>calibration}), performance: { now: () => time * 1000 },
    setTimeout:()=>0,
    window: { innerWidth: 1280, innerHeight: 720 }, document: { hidden:false, addEventListener() {}, getElementById: element },
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
  const source = fs.readFileSync(new URL('./debug.html', import.meta.url), 'utf8').split('<script type="module">')[1].split('</script>')[0].replace(/^import .*;\r?\n/gm, '').replaceAll('await fetch(', 'fetch(').replace('await response.json()', 'response.json()');
  read(source);
  return { read, key: code => handlers.keydown({ code, preventDefault() {} }),
    frame: t => { time = t; next(); }, resize: () => handlers.resize() };
}
test('maze clear enters the hunt, contact retries, and survival advances', () => {
  const p = page(); p.key('Escape'); p.key('Escape');
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

test('opening blocks maze movement and timer until tutorial is dismissed', () => {
 const p=page();const start=p.read('JSON.stringify(mazeState.hero)');p.key('KeyD');
 for(let i=1;i<=450;i++)p.frame(i/20);
 assert.equal(p.read('intro.state.phase'),'tutorial');
 assert.equal(p.read('mazeState.elapsed'),0);
 assert.equal(p.read('JSON.stringify(mazeState.hero)'),start);
 p.key('Escape');p.frame(23);assert.equal(p.read('intro.state.phase'),'done');
 assert.equal(p.read('mazeState.elapsed'),0);
 p.key('KeyD');p.frame(23.05);assert.notEqual(p.read('JSON.stringify(mazeState.hero)'),start);
});
test('replaying the opening resets level one without replaying on normal retry',()=>{
 const p=page();p.key('Digit2');p.frame(.1);p.key('KeyI');p.frame(.2);
 assert.equal(p.read('levelIndex'),0);assert.equal(p.read('intro.state.phase'),'cinematic');
 p.key('Escape');p.key('Escape');p.key('KeyR');p.frame(.3);
 assert.equal(p.read('intro.state.phase'),'done');
});

test('last tutorial gesture dismisses overlay and releases gameplay automatically',()=>{
 const p=page();p.key('Escape');
 p.read("intro.state.step=4; intro.state.control='keyboard'; intro.state.hold=0.55");
 p.frame(0.05);
 assert.equal(p.read('intro.state.phase'),'done');
 assert.equal(p.read("document.getElementById('lesson-card').style.opacity"),'0');
 assert.equal(p.read("document.getElementById('lesson-card').style.pointerEvents"),'none');
 assert.equal(p.read('mazeState.elapsed'),0);
 const start=p.read('JSON.stringify(mazeState.hero)');p.key('KeyD');p.frame(.1);
 assert.notEqual(p.read('JSON.stringify(mazeState.hero)'),start);
});

test('entering level three starts the virtual TK finale without rover activation', () => {
  const p=page();p.key('Digit3');p.frame(.1);
  assert.equal(p.read('LEVELS.length'),3);
  assert.equal(p.read('isPhysicalBoss()'),false);
  assert.equal(p.read('tkBoss.state.phase'),'warning');
  assert.equal(p.read('tkBoss.state.message'),'BOSS AWAKENED');
  assert.equal(p.read('ws.sent.every(m=>m.active !== true)'),true);
  p.read('hero.position.x=5');for(let i=3;i<=21;i++)p.frame(i/20);
  assert.equal(p.read('tkBoss.state.message'),'DODGED!');
});

test('surviving level three completes the game and retry resets three health', () => {
  const p=page();p.key('Digit3');p.frame(.1);
  p.read('hero.position.x=5; tkBoss.state.elapsed=29.96');p.frame(.15);
  assert.equal(p.read('tkBoss.state.phase'),'victory');
  p.frame(2.8);
  assert.equal(p.read('allCleared'),true);
  p.key('KeyR');p.frame(2.9);
  assert.equal(p.read('tkBoss.state.health'),3);
  assert.equal(p.read('tkBoss.state.phase'),'warning');
  assert.equal(p.read('allCleared'),false);
});
