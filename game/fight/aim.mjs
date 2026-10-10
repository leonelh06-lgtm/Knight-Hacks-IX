function aimAt(boss, p0, offX, offZ) {
  const tx = p0.x + offX, tz = p0.z + offZ;
  const len = Math.hypot(tx - boss.x, tz - boss.z) || 1;
  return { x: (tx - boss.x) / len, z: (tz - boss.z) / len };
}
function frame(boss, p0) {                       // unit vector to the player + its side vector
  const dx = p0.x - boss.x, dz = p0.z - boss.z, d = Math.hypot(dx, dz) || 1;
  const ax = dx / d, az = dz / d;
  return { ax, az, sx: -az, sz: ax };            // sx,sz = the predictor's PLUS side
}
export function makeRandomShift(rand = Math.random, shift = 2) {
  return (boss, p0) => {
    const f = frame(boss, p0), s = rand() < 0.5 ? 1 : -1;
    return aimAt(boss, p0, f.sx * s * shift, f.sz * s * shift);
  };
}
export function makeAdaptive(predictor, { rand = Math.random, shift = 2, minN = 2, minConf = 0.5 } = {}) {
  const fallback = makeRandomShift(rand, shift);
  return (boss, p0) => {
    const { dir, confidence, n } = predictor.predict();
    if (n < minN || confidence < minConf || dir === 'STAY') return fallback(boss, p0);
    const f = frame(boss, p0);
    const v = dir === 'PLUS' ? [f.sx, f.sz] : dir === 'MINUS' ? [-f.sx, -f.sz]
            : dir === 'AWAY' ? [f.ax, f.az] : [-f.ax, -f.az];
    return aimAt(boss, p0, v[0] * shift, v[1] * shift);
  };
}

// Neither chooser above checks that the player has anywhere left to dodge to.
// withEscapeCheck() wraps a chooser and re-rolls (up to `retries` times) if the
// aim it picked leaves no reachable point outside the cone within the
// walkable floor/pillars, given how far the player can move before it fires.
function inCone(boss, aim, halfAngle, range, p) {
  const dx = p.x - boss.x, dz = p.z - boss.z, d = Math.hypot(dx, dz);
  if (d > range) return false;
  if (d < 1e-6) return true;
  const cos = Math.max(-1, Math.min(1, (dx * aim.x + dz * aim.z) / d));
  return Math.acos(cos) <= halfAngle;
}
function insideFloor(p, floor, heroR) {
  if (!floor) return true;
  const rx = Math.max(1e-6, floor.rx - heroR), rz = Math.max(1e-6, floor.rz - heroR);
  const dx = (p.x - floor.cx) / rx, dz = (p.z - floor.cz) / rz;
  return dx * dx + dz * dz <= 1;
}
function clearOfPillars(p, pillars, heroR) {
  return (pillars || []).every((c) => Math.hypot(p.x - c.cx, p.z - c.cz) >= c.r + heroR);
}
export function hasEscape(boss, p0, aim, { halfAngle, range, floor, pillars, heroR = 0, reach, samples = 16 }) {
  if (!inCone(boss, aim, halfAngle, range, p0)) return true; // staying put already escapes
  for (let i = 0; i < samples; i++) {
    const ang = (i / samples) * Math.PI * 2;
    const p = { x: p0.x + Math.cos(ang) * reach, z: p0.z + Math.sin(ang) * reach };
    if (!insideFloor(p, floor, heroR) || !clearOfPillars(p, pillars, heroR)) continue;
    if (!inCone(boss, aim, halfAngle, range, p)) return true;
  }
  return false;
}
export function withEscapeCheck(chooseFn, escapeConfig, retries = 5) {
  return (boss, p0) => {
    let aim = chooseFn(boss, p0);
    if (!aim) return aim; // null means "fight.js aims straight at the player", nothing to re-roll
    for (let i = 0; i < retries && !hasEscape(boss, p0, aim, escapeConfig); i++) aim = chooseFn(boss, p0);
    return aim;
  };
}
