// Level 2: survive two roaming hunters. Contact is always lethal.
// The controller keeps the same { state, start, reset, update } interface.
export const DEFAULTS = {
  SURVIVE_TIME: 20, DEATH_CARD_HOLD: 1.6,
  HERO_R: 0.3, HERO_SPEED: 3, HUNTER_R: 0.39,
  SPEED_START: 1.25, SPEED_END: 1.85, LUNGE_SPEED: 3.8,
  WAKE_TIME: 0.9, WARNING_TIME: 0.8, LUNGE_TIME: 0.38, RECOVER_TIME: 0.7,
  FLOOR: { cx: 0.50, cz: 0.535, rx: 0.45, rz: 0.357 },
  PLATFORM: { cx: 0.50, cz: 0.23, r: 0.134 },
};
export function floorFromRoom(room, f = DEFAULTS.FLOOR) {
  const w = room.maxX - room.minX, h = room.maxZ - room.minZ;
  return { cx: room.minX + f.cx * w, cz: room.minZ + f.cz * h, rx: f.rx * w, rz: f.rz * h };
}
function clampFloor(p, floor, radius) {
  const rx = Math.max(0.01, floor.rx - radius), rz = Math.max(0.01, floor.rz - radius);
  const x = (p.x - floor.cx) / rx, z = (p.z - floor.cz) / rz, d = Math.hypot(x, z);
  if (d > 1) { p.x = floor.cx + x / d * rx; p.z = floor.cz + z / d * rz; }
  return p;
}
// Relative swept-circle collision prevents skipping through a hunter at low FPS.
export function sweptContact(a0, a1, b0, b1, radius) {
  const x = a0.x - b0.x, z = a0.z - b0.z;
  const dx = a1.x - b1.x - x, dz = a1.z - b1.z - z;
  const d2 = dx * dx + dz * dz;
  const u = d2 > 0 ? Math.max(0, Math.min(1, -(x * dx + z * dz) / d2)) : 0;
  return Math.hypot(x + u * dx, z + u * dz) <= radius;
}
export function createL2(config) {
  const cfg = { ...DEFAULTS, ...config }, hero = cfg.hero;
  const floor = floorFromRoom(cfg.room, cfg.FLOOR);
  const spaceScale = Math.min(1, Math.max(0.65, floor.rx / 6.5));
  const spawn = clampFloor({ x: floor.cx, z: floor.cz - floor.rz * 0.72 }, floor, cfg.HERO_R);
  const state = { phase: 'IDLE', elapsed: 0, remaining: cfg.SURVIVE_TIME,
    duration: cfg.SURVIVE_TIME, deaths: 0, floor, hunters: [], danger: 0,
    message: 'KEEP MOVING', t: 0, deadAt: 0, deadUntil: 0 };
  let lastTime = 0, previousHero = { ...hero.position };
  function reset() {
    state.phase = 'IDLE'; state.elapsed = 0; state.remaining = cfg.SURVIVE_TIME; state.danger = 0;
    state.hunters = [-1, 1].map((side, i) => ({
      name: i === 0 ? 'STALKER' : 'PROWLER',
      position: clampFloor({ x: floor.cx + side * floor.rx * 0.68, z: floor.cz + floor.rz * 0.25 }, floor, cfg.HUNTER_R),
      radius: cfg.HUNTER_R, mode: 'hunt', modeTime: 0,
      nextLunge: 3.1 + i * 2, direction: { x: 0, z: -1 }, trail: [], trailTime: 0,
    }));
  }
  function start(now) {
    reset(); state.phase = 'PLAYING'; state.t = now; lastTime = now;
    Object.assign(hero.position, spawn); previousHero = { ...spawn };
  }
  function die() {
    state.phase = 'DEAD'; state.deaths++; state.deadAt = state.t;
    state.deadUntil = state.t + cfg.DEATH_CARD_HOLD; state.message = 'CAUGHT';
  }
  function update(now, frameDt) {
    // Clamp game time together with movement after tab suspension.
    const dt = Math.max(0, Math.min(0.05, frameDt ?? now - lastTime));
    lastTime = now; state.t = now;
    if (state.phase === 'DEAD') { if (now >= state.deadUntil) start(now); return; }
    if (state.phase !== 'PLAYING' || dt === 0) return;
    const endHero = { ...hero.position };
    const velocity = { x: (endHero.x - previousHero.x) / dt, z: (endHero.z - previousHero.z) / dt };
    const vlen = Math.hypot(velocity.x, velocity.z);
    if (vlen > cfg.HERO_SPEED) { velocity.x *= cfg.HERO_SPEED / vlen; velocity.z *= cfg.HERO_SPEED / vlen; }
    const steps = Math.max(1, Math.ceil(dt / (1 / 120))), subDt = dt / steps;
    for (let step = 0; step < steps && state.phase === 'PLAYING'; step++) {
      const u0 = step / steps, u1 = (step + 1) / steps;
      const heroAt = u => ({ x: previousHero.x + (endHero.x - previousHero.x) * u, z: previousHero.z + (endHero.z - previousHero.z) * u });
      const h0 = heroAt(u0), h1 = heroAt(u1);
      state.elapsed = Math.min(cfg.SURVIVE_TIME, state.elapsed + subDt);
      for (let i = 0; i < state.hunters.length; i++) {
        const h = state.hunters[i], before = { ...h.position };
        const progress = state.elapsed / cfg.SURVIVE_TIME;
        let speed = (cfg.SPEED_START + (cfg.SPEED_END - cfg.SPEED_START) * progress) * (i ? 0.94 : 1) * spaceScale;
        h.modeTime += subDt;
        if (h.mode === 'hunt' && state.elapsed >= h.nextLunge) { h.mode = 'warning'; h.modeTime = 0; }
        if (h.mode === 'warning' && h.modeTime >= cfg.WARNING_TIME) { h.mode = 'lunge'; h.modeTime = 0; }
        if (h.mode === 'lunge' && h.modeTime >= cfg.LUNGE_TIME) { h.mode = 'recover'; h.modeTime = 0; }
        if (h.mode === 'recover' && h.modeTime >= cfg.RECOVER_TIME) {
          h.mode = 'hunt'; h.modeTime = 0; h.nextLunge = state.elapsed + 3.3 - progress * 0.7;
        }
        if (h.mode === 'hunt' || (h.mode === 'warning' && h.modeTime < cfg.WARNING_TIME - 0.3)) {
          let target = { ...h1 };
          if (i && h.mode === 'hunt') {
            // Orbit the player's flank and anticipate their route, rather than stacking on the stalker.
            const angle = state.elapsed * 0.85;
            target.x += velocity.x * 0.7 + Math.cos(angle) * 1.2;
            target.z += velocity.z * 0.7 + Math.sin(angle) * 1.2;
            clampFloor(target, floor, h.radius);
          }
          const dx = target.x - h.position.x, dz = target.z - h.position.z, len = Math.hypot(dx, dz);
          if (len > 0.001) h.direction = { x: dx / len, z: dz / len };
          speed = Math.min(speed, len / subDt);
        }
        if (h.mode === 'warning') speed = 0;
        if (h.mode === 'lunge') speed = cfg.LUNGE_SPEED * spaceScale;
        if (h.mode === 'recover') speed *= 0.22;
        if (state.elapsed < cfg.WAKE_TIME) speed = 0;
        h.position.x += h.direction.x * speed * subDt;
        h.position.z += h.direction.z * speed * subDt;
        clampFloor(h.position, floor, h.radius);
        h.trailTime += subDt;
        if (h.trailTime >= 0.045) {
          h.trail.push({ ...h.position }); if (h.trail.length > 13) h.trail.shift(); h.trailTime = 0;
        }
        if (sweptContact(h0, h1, before, h.position, cfg.HERO_R + h.radius)) { die(); break; }
      }
      // Contact on the last timestep is fatal; success cannot overwrite death.
      if (state.phase === 'PLAYING' && state.elapsed >= cfg.SURVIVE_TIME - 1e-8) {
        state.elapsed = cfg.SURVIVE_TIME; state.phase = 'CLEARED'; state.message = 'YOU SURVIVED';
      }
    }
    previousHero = endHero;
    state.remaining = Math.max(0, cfg.SURVIVE_TIME - state.elapsed);
    const gap = Math.min(...state.hunters.map(h => Math.hypot(h.position.x - endHero.x, h.position.z - endHero.z) - h.radius - cfg.HERO_R));
    state.danger = Math.max(0, Math.min(1, 1 - gap / 2.2));
  }
  reset();
  return { state, start, reset, update };
}
