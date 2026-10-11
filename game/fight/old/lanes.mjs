// lanes.mjs: Level 1's lane-crossing mechanic (rolling boulders across
// horizontal bands). Pure geometry (boulder positions, hit test, band
// validation) plus a createFight-shaped controller (createLanes: { state,
// start, reset, update }) so debug.html can drive it exactly like fight.js's
// createFight or holes.mjs's createCrossing. Nothing here imports fight.js.

const KNOCKBACK_S = 0.5; // slide-back duration on a hit

// The floor is an ellipse; this is its x half-width at a given z (0 past the
// ellipse's top/bottom). Same helper shape as holes.mjs used.
export function floorHalfWidthAtZ(z, floor) {
  const t = 1 - ((z - floor.cz) / floor.rz) ** 2;
  return t > 0 ? floor.rx * Math.sqrt(t) : 0;
}

// Bands roll in alternating directions: even index (0-based, ordered start->goal) rolls +x, odd rolls -x.
export function bandDir(index) { return index % 2 === 0 ? 1 : -1; }

// Per-boulder state in a band at time t: evenly spaced across the band's
// actual rendered width (so the wrap is seamless), each with its wrap edge
// and the time remaining until it reaches that edge (for the warning marker).
export function boulderStates(band, floor, dir, t) {
  const halfW = floorHalfWidthAtZ(band.z, floor);
  const laneWidth = halfW * 2;
  const spacing = laneWidth / band.boulders;
  const out = [];
  for (let i = 0; i < band.boulders; i++) {
    let x = (-halfW + i * spacing + band.speed * t * dir) % laneWidth;
    if (x < -halfW) x += laneWidth;
    if (x >= halfW) x -= laneWidth;
    const timeToWrap = dir > 0 ? (halfW - x) / band.speed : (x + halfW) / band.speed;
    out.push({ x: x + floor.cx, z: band.z, timeToWrap, wrapEdgeX: (dir > 0 ? -halfW : halfW) + floor.cx });
  }
  return out;
}

export function isHitByBand(p, band, floor, dir, t, heroR) {
  return boulderStates(band, floor, dir, t).some((b) => Math.hypot(p.x - b.x, p.z - b.z) <= band.radius + heroR);
}

// Warning markers: boulders within `leadTime` seconds of wrapping back in at
// their entering edge. Returns [{ x, z, timeToWrap }] in world units.
export function upcomingEntryWarnings(level, floor, t, leadTime = 1.0) {
  const bands = orderedBands(level);
  const warnings = [];
  bands.forEach((band, i) => {
    const dir = bandDir(i);
    for (const b of boulderStates(band, floor, dir, t)) {
      if (b.timeToWrap > 0 && b.timeToWrap <= leadTime) warnings.push({ x: b.wrapEdgeX, z: band.z, timeToWrap: b.timeToWrap });
    }
  });
  return warnings;
}

// Bands ordered from the start side (high z) to the goal side (low z); index
// in this order is what bandDir() and the knockback "previous strip" use.
function orderedBands(level) {
  return [...level.bands].sort((a, b) => b.z - a.z);
}

// Returns warning strings (empty = all clear): per-band gap/speed crossability
// ("Startup check... gap/speed math") and inter-band safe-strip width (>= 4x
// hero diameter).
export function validateBands(level, { floor, heroR, heroSpeed }) {
  const warnings = [];
  const minStrip = 8 * heroR; // 4x hero diameter
  const bands = orderedBands(level);
  for (let i = 0; i < bands.length; i++) {
    const band = bands[i];
    const halfW = floorHalfWidthAtZ(band.z, floor);
    const spacing = (halfW * 2) / band.boulders;
    const actualGap = spacing - 2 * band.radius;
    if (actualGap < band.gap) {
      warnings.push(`band ${i} (z=${band.z}): derived gap ${actualGap.toFixed(2)}u is smaller than its configured minimum ${band.gap.toFixed(2)}u`);
    }
    const crossTime = band.height / heroSpeed, openTime = actualGap / band.speed;
    if (crossTime > openTime) {
      warnings.push(`band ${i} (z=${band.z}): impossible to cross — needs ${crossTime.toFixed(2)}s, gap is only open ${openTime.toFixed(2)}s`);
    }
    if (i > 0) {
      const prev = bands[i - 1];
      const strip = (prev.z - prev.height / 2) - (band.z + band.height / 2);
      if (strip < minStrip) warnings.push(`safe strip between band ${i - 1} and band ${i} is ${strip.toFixed(2)}u, need ${minStrip.toFixed(2)}u`);
    }
  }
  return warnings;
}

// Mirrors fight.js's createFight / holes.mjs's createCrossing: { state, start,
// reset, update }. state.phase is 'idle' | 'playing' | 'knockback' | 'victory'.
export function createLanes(level, hero, { onHit, onWin } = {}) {
  const bands = orderedBands(level);
  function safeZBehind(bandIndex) {
    if (bandIndex === 0) return level.start.z;
    const prev = bands[bandIndex - 1];
    return prev.z - prev.height / 2 - 0.3; // just inside the strip behind the band that hit
  }
  const c = {};
  function reset() {
    Object.assign(c, {
      phase: 'idle', message: 'Press B to start', hits: 0, startedAt: 0, spin: 0,
      knockFromX: 0, knockFromZ: 0, knockToX: 0, knockToZ: 0, knockStartAt: 0,
    });
  }
  function start(now) {
    reset();
    c.phase = 'playing'; c.message = `Reach the platform: ${level.name}`; c.startedAt = now;
    hero.position.x = level.start.x; hero.position.z = level.start.z;
  }
  function update(now, floor, heroR) {
    if (c.phase === 'idle' || c.phase === 'victory') return;
    if (c.phase === 'knockback') {
      const tt = Math.min(1, (now - c.knockStartAt) / KNOCKBACK_S);
      hero.position.x = c.knockFromX + (c.knockToX - c.knockFromX) * tt;
      hero.position.z = c.knockFromZ + (c.knockToZ - c.knockFromZ) * tt;
      c.spin = tt < 1 ? tt * Math.PI * 4 : 0; // a couple of spins through the slide, settles at the end
      if (tt >= 1) { c.phase = 'playing'; c.message = `Reach the platform: ${level.name}`; c.spin = 0; }
      return;
    }
    for (let i = 0; i < bands.length; i++) {
      const band = bands[i];
      if (Math.abs(hero.position.z - band.z) > band.height / 2) continue;
      if (!isHitByBand(hero.position, band, floor, bandDir(i), now, heroR)) continue;
      c.phase = 'knockback'; c.hits += 1; c.message = 'KNOCKED BACK!'; c.knockStartAt = now;
      c.knockFromX = hero.position.x; c.knockFromZ = hero.position.z;
      c.knockToX = level.start.x; c.knockToZ = safeZBehind(i);
      onHit?.({ hits: c.hits, t: now });
      return;
    }
    const g = level.goal;
    if (g && Math.hypot(hero.position.x - g.x, hero.position.z - g.z) <= g.r) {
      c.phase = 'victory'; c.message = 'REACHED THE PLATFORM';
      onWin?.({ t: now, elapsed: now - c.startedAt, hits: c.hits });
    }
  }
  reset();
  return { state: c, start, reset, update };
}
