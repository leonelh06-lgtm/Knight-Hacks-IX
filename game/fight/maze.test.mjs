// maze.test.mjs: run with `node maze.test.mjs`. Exits non-zero on failure.
//
// Check 3's bot is NOT a model of a real player -- it's a simple
// direction-holds-with-random-lag automaton used only to sanity-check that
// the fixed layout + collision/lane-assist physics are actually walkable at
// the configured hero speed without ever tunneling through a wall or getting
// permanently stuck.
import assert from 'node:assert';
import {
  COLS, ROWS, parseMaze, mirrorMaze, isPerfectMaze, edgeCount, findRoute, toRuns, createMaze, step,
} from './maze.mjs';

let failures = 0;
function check(label, fn) {
  try { fn(); console.log(`ok - ${label}`); }
  catch (e) { failures++; console.error(`FAIL - ${label}: ${e.message}`); }
}

// --- 1: perfect maze -------------------------------------------------------
const maze = parseMaze();
check('exactly one simple path (connected tree, cells-1 edges)', () => {
  assert.equal(edgeCount(maze), COLS * ROWS - 1, 'edge count');
  assert.ok(isPerfectMaze(maze), 'not connected / not a tree');
});
check('mirrored maze is also a valid perfect maze', () => {
  const m = mirrorMaze(maze);
  assert.equal(edgeCount(m), COLS * ROWS - 1, 'mirrored edge count');
  assert.ok(isPerfectMaze(m), 'mirrored maze not a perfect maze');
});

// --- 2: route requires all four gestures ------------------------------------
const route = findRoute(maze);
const runs = toRuns(route);
check('route requires all 4 gestures, >=2 runs each, >=12 runs total', () => {
  const counts = { UP: 0, DOWN: 0, LEFT: 0, RIGHT: 0 };
  for (const r of runs) counts[r.dir]++;
  console.log('  runs:', runs.map((r) => r.dir[0] + r.len).join(' '));
  console.log(`  totals: moves=${route.length} runs=${runs.length} UP=${counts.UP} DOWN=${counts.DOWN} LEFT=${counts.LEFT} RIGHT=${counts.RIGHT}`);
  for (const dir of ['UP', 'DOWN', 'LEFT', 'RIGHT']) assert.ok(counts[dir] >= 2, `expected >=2 ${dir} runs, got ${counts[dir]}`);
  assert.ok(runs.length >= 12, `expected >=12 runs total, got ${runs.length}`);
  assert.equal(route.length, 29, `expected 29 moves, got ${route.length}`);
  assert.equal(runs.length, 19, `expected 19 runs, got ${runs.length}`);
});

// --- 3: physics sim with a lagged bot ---------------------------------------
function mulberry32(seed) {
  let a = seed >>> 0;
  return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const DIR_VEC = { UP: { x: 0, z: -1 }, DOWN: { x: 0, z: 1 }, LEFT: { x: -1, z: 0 }, RIGHT: { x: 1, z: 0 } };
const DT = 1 / 120; // fine fixed step so substep-tunneling would actually show up, not get hidden by a coarse step
const HERO_R = 0.3;
const HERO_SPEED = 2.4;
const ROOM_W = 20, ROOM_H = 12; // representative arena size
const MAX_T = 60; // generous ceiling; a real failure shows up long before this

// Direction-transition state machine: MOVING (holding `heldDir`) -> once the
// route calls for a different direction -> HOLDING_OLD (keeps the old
// direction for a random 0.15-0.45s, i.e. "simulated gesture lag") ->
// PAUSED (zero velocity for a random 0-0.3s, "starts each run with a delay")
// -> MOVING again with the new direction.
function runBot(seed) {
  const rng = mulberry32(seed);
  const state = createMaze({ roomW: ROOM_W, roomH: ROOM_H, heroSpeed: HERO_SPEED, laneAssist: 0.6, mirrored: false });
  state.heroR = HERO_R;
  const { P, originX, originZ } = state.geom;
  const cellOf = (p) => ({ c: Math.floor((p.x - originX) / P), r: Math.floor((p.z - originZ) / P) });

  let moveIdx = 0;
  let prevCell = cellOf(state.hero);
  let transPhase = 'PAUSED', transUntil = rng() * 0.3, heldDir = null; // initial 0-0.3s start delay
  let t = 0, stuckClock = 0, lastPos = { x: state.hero.x, z: state.hero.z };
  let tunneled = false, stuckTooLong = false;

  while (state.phase !== 'CLEARED' && t < MAX_T) {
    const cell = cellOf(state.hero);
    if (cell.c !== prevCell.c || cell.r !== prevCell.r) { moveIdx = Math.min(moveIdx + 1, route.length - 1); prevCell = cell; }
    const desiredDir = route[Math.min(moveIdx, route.length - 1)];

    if (transPhase === 'MOVING' && desiredDir !== heldDir) { transPhase = 'HOLDING_OLD'; transUntil = t + 0.15 + rng() * 0.3; }
    if (transPhase === 'HOLDING_OLD' && t >= transUntil) { transPhase = 'PAUSED'; transUntil = t + rng() * 0.3; }
    if (transPhase === 'PAUSED' && t >= transUntil) { transPhase = 'MOVING'; heldDir = desiredDir; }
    const v = transPhase === 'MOVING' ? DIR_VEC[heldDir] : (heldDir ? DIR_VEC[heldDir] : { x: 0, z: 0 });

    const beforeHero = { x: state.hero.x, z: state.hero.z };
    step(state, DT, { vx: v.x * HERO_SPEED, vz: v.z * HERO_SPEED, handActive: true });
    t += DT;

    const moved = Math.hypot(state.hero.x - beforeHero.x, state.hero.z - beforeHero.z);
    if (moved > HERO_SPEED * DT + 0.15) tunneled = true; // far more displacement than physically possible without a hole

    const d = Math.hypot(state.hero.x - lastPos.x, state.hero.z - lastPos.z);
    if (d < 0.01) stuckClock += DT; else { stuckClock = 0; lastPos = { x: state.hero.x, z: state.hero.z }; }
    if (stuckClock > 2) stuckTooLong = true;
  }
  return { cleared: state.phase === 'CLEARED', elapsed: state.elapsed, tunneled, stuckTooLong, timedOut: t >= MAX_T };
}

check('500-run physics sim: 100% clear, no 2s+ stuck, no tunneling', () => {
  const N = 500;
  let cleared = 0, stuck = 0, tunneled = 0, timedOut = 0;
  const times = [];
  for (let s = 0; s < N; s++) {
    const r = runBot(s * 7919 + 13);
    if (r.cleared) { cleared++; times.push(r.elapsed); }
    if (r.stuckTooLong) stuck++;
    if (r.tunneled) tunneled++;
    if (r.timedOut) timedOut++;
  }
  times.sort((a, b) => a - b);
  const min = times[0], max = times[times.length - 1], median = times[Math.floor(times.length / 2)];
  console.log(`  cleared ${cleared}/${N} | stuck>2s: ${stuck} | tunneled: ${tunneled} | timed out: ${timedOut}`);
  console.log(`  completion time (s): min=${min?.toFixed(2)} median=${median?.toFixed(2)} max=${max?.toFixed(2)}`);
  assert.equal(cleared, N, `expected 100% clear, got ${cleared}/${N}`);
  assert.equal(stuck, 0, `${stuck} runs were stuck against a wall for >2s`);
  assert.equal(tunneled, 0, `${tunneled} runs tunneled through a wall`);
});

if (failures) { console.error(`\n${failures} check(s) failed.`); process.exit(1); }
console.log('\nmaze.test.mjs: all checks passed.');
