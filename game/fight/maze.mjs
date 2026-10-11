// maze.mjs: pure logic for the Level 1 hedge maze. No DOM. Parses the fixed
// ASCII layout into a cell graph and wall/post geometry, then exposes
// createMaze(config)/step(state, dt, input) in the same shape every other
// level mechanic in this game uses (fight.js's createFight, bridge.mjs's
// createBridge, etc.): { state, step } with a plain-data state object.

export const COLS = 9, ROWS = 6;
const WALL_POST_R = 0.26;
const MIN_WALL_T = 0.2;
const MIN_CORRIDOR = 1.2;

export const ASCII_MAZE = [
  '###################',
  '#   #           # #',
  '### # # # ##### # #',
  '#   # # # #   #   #',
  '# ##### ### # ### #',
  '#     #     #   # G',
  '##### # ####### # #',
  'S   # #     #   # #',
  '# ### ####### ### #',
  '# #   #     # #   #',
  '# # ### ### # # ###',
  '#       #     #   #',
  '###################',
].join('\n');

// --- parsing -----------------------------------------------------------
// eastOpen[c][r]: true if cell (c,r) and (c+1,r) are connected (no wall).
// southOpen[c][r]: true if cell (c,r) and (c,r+1) are connected.
export function parseMaze(ascii = ASCII_MAZE) {
  const rows = ascii.split('\n');
  if (rows.length !== 2 * ROWS + 1) throw new Error(`maze.mjs: expected ${2 * ROWS + 1} ASCII rows, got ${rows.length}`);
  for (const row of rows) if (row.length !== 2 * COLS + 1) throw new Error(`maze.mjs: expected ${2 * COLS + 1}-char ASCII rows, got ${row.length}: "${row}"`);
  const eastOpen = Array.from({ length: COLS }, () => Array(ROWS).fill(false));
  const southOpen = Array.from({ length: COLS }, () => Array(ROWS).fill(false));
  let start = null, goal = null;
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      const cx = 2 * c + 1, cy = 2 * r + 1;
      if (c < COLS - 1) eastOpen[c][r] = rows[cy][cx + 1] !== '#';
      if (r < ROWS - 1) southOpen[c][r] = rows[cy + 1][cx] !== '#';
      if (c === 0 && rows[cy][cx - 1] === 'S') start = { c, r };
      if (c === COLS - 1 && rows[cy][cx + 1] === 'G') goal = { c, r };
    }
  }
  if (!start) throw new Error('maze.mjs: no S gate found on the west boundary');
  if (!goal) throw new Error('maze.mjs: no G gate found on the east boundary');
  return { cols: COLS, rows: ROWS, eastOpen, southOpen, start, goal, mirrored: false };
}

// Mirrors the maze left-right: walls, and the S/G gates (which stay tied to
// their own cell, now on the opposite side -- "swaps start and goal sides").
export function mirrorMaze(maze) {
  const eastOpen = Array.from({ length: COLS }, () => Array(ROWS).fill(false));
  const southOpen = Array.from({ length: COLS }, () => Array(ROWS).fill(false));
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS - 1; c++) eastOpen[c][r] = maze.eastOpen[COLS - 2 - c][r];
    for (let c = 0; c < COLS; c++) southOpen[c][r] = maze.southOpen[COLS - 1 - c][r];
  }
  return {
    cols: COLS, rows: ROWS, eastOpen, southOpen, mirrored: !maze.mirrored,
    start: { c: COLS - 1 - maze.start.c, r: maze.start.r },
    goal: { c: COLS - 1 - maze.goal.c, r: maze.goal.r },
  };
}

// --- graph / route -------------------------------------------------------
export function edgeCount(maze) {
  let n = 0;
  for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) {
    if (c < COLS - 1 && maze.eastOpen[c][r]) n++;
    if (r < ROWS - 1 && maze.southOpen[c][r]) n++;
  }
  return n;
}
export function neighbors(maze, c, r) {
  const out = [];
  if (c > 0 && maze.eastOpen[c - 1][r]) out.push({ c: c - 1, r, dir: 'LEFT' });
  if (c < COLS - 1 && maze.eastOpen[c][r]) out.push({ c: c + 1, r, dir: 'RIGHT' });
  if (r > 0 && maze.southOpen[c][r - 1]) out.push({ c, r: r - 1, dir: 'UP' });
  if (r < ROWS - 1 && maze.southOpen[c][r]) out.push({ c, r: r + 1, dir: 'DOWN' });
  return out;
}
// True iff the maze is a "perfect" maze: connected with exactly cells-1 edges (a tree).
export function isPerfectMaze(maze) {
  const total = COLS * ROWS;
  if (edgeCount(maze) !== total - 1) return false;
  const seen = new Set(['0,0']);
  const stack = [{ c: 0, r: 0 }];
  while (stack.length) {
    const cur = stack.pop();
    for (const n of neighbors(maze, cur.c, cur.r)) {
      const k = `${n.c},${n.r}`;
      if (!seen.has(k)) { seen.add(k); stack.push(n); }
    }
  }
  return seen.size === total;
}
// The unique simple path start->goal (the maze is a tree, so there's exactly
// one), as an ordered list of 'UP'|'DOWN'|'LEFT'|'RIGHT' single-cell moves.
export function findRoute(maze) {
  const key = (c, r) => `${c},${r}`;
  const parent = new Map([[key(maze.start.c, maze.start.r), null]]);
  const stack = [maze.start];
  while (stack.length) {
    const cur = stack.pop();
    if (cur.c === maze.goal.c && cur.r === maze.goal.r) break;
    for (const n of neighbors(maze, cur.c, cur.r)) {
      const k = key(n.c, n.r);
      if (!parent.has(k)) { parent.set(k, { from: cur, dir: n.dir }); stack.push(n); }
    }
  }
  const goalKey = key(maze.goal.c, maze.goal.r);
  if (!parent.has(goalKey)) throw new Error('maze.mjs: no route from start to goal');
  const moves = [];
  let k = goalKey;
  while (parent.get(k) !== null) {
    const { from, dir } = parent.get(k);
    moves.unshift(dir);
    k = key(from.c, from.r);
  }
  return moves;
}
// Collapses consecutive same-direction moves into runs: [{ dir, len }, ...].
export function toRuns(moves) {
  const runs = [];
  for (const dir of moves) {
    if (runs.length && runs[runs.length - 1].dir === dir) runs[runs.length - 1].len++;
    else runs.push({ dir, len: 1 });
  }
  return runs;
}

// --- geometry (world units, local to the maze before centering) ----------
function hasVerticalWall(maze, c, r) { // x = c*P line, spanning row r
  if (r < 0 || r >= ROWS) return false;
  if (c === 0) return maze.start.r !== r;
  if (c === COLS) return maze.goal.r !== r;
  if (c < 0 || c > COLS) return false;
  return !maze.eastOpen[c - 1][r];
}
function hasHorizontalWall(maze, c, r) { // z = r*P line, spanning column c
  if (c < 0 || c >= COLS) return false;
  if (r === 0 || r === ROWS) return true; // north/south boundary: always solid, no gates
  if (r < 0 || r > ROWS) return false;
  return !maze.southOpen[c][r - 1];
}
// Builds wall rectangles ({cx,cz,hw,hh}), corner posts ({x,z,r}), the cell
// pitch P, and a wall thickness (shrunk from WALL_T if the corridor would be
// narrower than MIN_CORRIDOR -- logs a warning when that happens).
export function buildGeometry(maze, roomW, roomH, wallT = 0.32) {
  const P = Math.min(roomW / COLS, roomH / ROWS) * 0.97;
  const warnings = [];
  let WALL_T = wallT;
  if (P - WALL_T < MIN_CORRIDOR) {
    const shrunk = Math.max(MIN_WALL_T, P - MIN_CORRIDOR);
    warnings.push(`corridor clear width ${(P - WALL_T).toFixed(2)}u < ${MIN_CORRIDOR}u minimum; shrinking WALL_T ${WALL_T} -> ${shrunk.toFixed(2)}`);
    WALL_T = shrunk;
  }
  const mazeW = COLS * P, mazeH = ROWS * P;
  const originX = -mazeW / 2, originZ = -mazeH / 2; // caller centers this in the arena
  const walls = [];
  for (let c = 0; c <= COLS; c++) for (let r = 0; r < ROWS; r++) {
    if (!hasVerticalWall(maze, c, r)) continue;
    walls.push({ cx: originX + c * P, cz: originZ + (r + 0.5) * P, hw: WALL_T / 2, hh: P / 2 });
  }
  for (let c = 0; c < COLS; c++) for (let r = 0; r <= ROWS; r++) {
    if (!hasHorizontalWall(maze, c, r)) continue;
    walls.push({ cx: originX + (c + 0.5) * P, cz: originZ + r * P, hw: P / 2, hh: WALL_T / 2 });
  }
  const posts = [];
  for (let c = 0; c <= COLS; c++) for (let r = 0; r <= ROWS; r++) {
    if (hasVerticalWall(maze, c, r - 1) || hasVerticalWall(maze, c, r) || hasHorizontalWall(maze, c - 1, r) || hasHorizontalWall(maze, c, r)) {
      posts.push({ x: originX + c * P, z: originZ + r * P, r: WALL_POST_R });
    }
  }
  const cellCenter = (c, r) => ({ x: originX + (c + 0.5) * P, z: originZ + (r + 0.5) * P });
  return { P, WALL_T, originX, originZ, walls, posts, cellCenter, warnings };
}

// --- collision -------------------------------------------------------------
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
function pushOutOfRect(p, heroR, rect) {
  const cx = clamp(p.x, rect.cx - rect.hw, rect.cx + rect.hw);
  const cz = clamp(p.z, rect.cz - rect.hh, rect.cz + rect.hh);
  const dx = p.x - cx, dz = p.z - cz, d = Math.hypot(dx, dz);
  if (d >= heroR) return false;
  if (d < 1e-9) {
    const overlapX = rect.hw + heroR - Math.abs(p.x - rect.cx);
    const overlapZ = rect.hh + heroR - Math.abs(p.z - rect.cz);
    if (overlapX < overlapZ) p.x += Math.sign(p.x - rect.cx || 1) * overlapX;
    else p.z += Math.sign(p.z - rect.cz || 1) * overlapZ;
  } else {
    const push = heroR - d;
    p.x += (dx / d) * push; p.z += (dz / d) * push;
  }
  return true;
}
function pushOutOfPost(p, heroR, post) {
  const dx = p.x - post.x, dz = p.z - post.z, d = Math.hypot(dx, dz), minD = heroR + post.r;
  if (d >= minD) return false;
  if (d < 1e-9) { p.x += minD; } else { const push = minD - d; p.x += (dx / d) * push; p.z += (dz / d) * push; }
  return true;
}
export function resolveCollisions(p, heroR, geom, iterations = 3) {
  for (let i = 0; i < iterations; i++) {
    for (const w of geom.walls) pushOutOfRect(p, heroR, w);
    for (const post of geom.posts) pushOutOfPost(p, heroR, post);
  }
}

// --- level state -------------------------------------------------------
function starsFor(elapsed, thresholds) {
  if (elapsed <= thresholds.three) return 3;
  if (elapsed <= thresholds.two) return 2;
  return 1;
}

export function createMaze(config) {
  const maze = config.mirrored ? mirrorMaze(parseMaze()) : parseMaze();
  const geom = buildGeometry(maze, config.roomW, config.roomH, config.wallT ?? 0.32);
  const start = geom.cellCenter(maze.start.c, maze.start.r);
  const goal = geom.cellCenter(maze.goal.c, maze.goal.r);
  return {
    maze, geom, hero: { x: start.x, z: start.z }, goal, goalRadius: 0.8,
    heroSpeed: config.heroSpeed ?? 2.4, laneAssist: config.laneAssist ?? 0.6,
    phase: 'PLAYING', started: false, elapsed: 0, paused: false, noHandT: 0,
    stars: 0, starThresholds: config.starThresholds ?? { three: 40, two: 70 },
  };
}

// input = { vx, vz, handActive } where vx/vz are the existing pipeline's
// already-eased velocity components in world units/sec (debug.html passes
// heroVel.x/heroVel.z straight through -- this file never touches input).
export function step(state, dt, input) {
  const vx = (input && Number.isFinite(input.vx)) ? input.vx : 0;
  const vz = (input && Number.isFinite(input.vz)) ? input.vz : 0;
  const handActive = !!(input && input.handActive);
  if (handActive) state.noHandT = 0; else state.noHandT += dt;
  state.paused = state.noHandT > 0.8;

  if (state.phase === 'CLEARED') return state;
  if (!state.started && (Math.abs(vx) > 1e-3 || Math.abs(vz) > 1e-3)) state.started = true;
  if (state.started && !state.paused) state.elapsed += dt;

  const heroR = state.heroR ?? 0.3;
  const dist = Math.hypot(vx, vz) * dt;
  const steps = Math.max(1, Math.ceil(dist / 0.05));
  const subDt = dt / steps;
  for (let i = 0; i < steps; i++) {
    state.hero.x += vx * subDt; state.hero.z += vz * subDt;
    resolveCollisions(state.hero, heroR, state.geom, 3);
  }

  // LANE_ASSIST: pull the perpendicular coordinate toward the nearest cell
  // centerline while moving predominantly along one axis. Never applied with
  // no input; collision resolution above already guarantees it can't leave
  // the hero inside a wall (next step's resolveCollisions corrects it).
  if (Math.abs(vx) > 1e-3 || Math.abs(vz) > 1e-3) {
    const P = state.geom.P, assist = state.laneAssist;
    if (Math.abs(vx) > Math.abs(vz)) {
      const targetZ = state.geom.originZ + (Math.round((state.hero.z - state.geom.originZ) / P - 0.5) + 0.5) * P;
      const d = targetZ - state.hero.z;
      const maxSpeed = Math.min(Math.abs(d) * 6, 1.5 * assist);
      state.hero.z += Math.sign(d) * Math.min(Math.abs(d), maxSpeed * dt);
    } else if (Math.abs(vz) > Math.abs(vx)) {
      const targetX = state.geom.originX + (Math.round((state.hero.x - state.geom.originX) / P - 0.5) + 0.5) * P;
      const d = targetX - state.hero.x;
      const maxSpeed = Math.min(Math.abs(d) * 6, 1.5 * assist);
      state.hero.x += Math.sign(d) * Math.min(Math.abs(d), maxSpeed * dt);
    }
  }

  if (Math.hypot(state.hero.x - state.goal.x, state.hero.z - state.goal.z) <= state.goalRadius) {
    state.phase = 'CLEARED';
    state.stars = starsFor(state.elapsed, state.starThresholds);
  }
  return state;
}
