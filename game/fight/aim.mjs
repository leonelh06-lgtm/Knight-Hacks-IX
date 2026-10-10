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
