// TK's virtual survival encounter. All positions use the same room coordinates as Lenny.
export function createTKBoss({ hero, room, duration = 30, position = { x: 0, z: 0.7 } }) {
  const warning = 1, laser = 0.45, recover = 2;
  const state = { phase: 'idle', position: { ...position }, aim: { x: 0, z: 1 },
    halfAngle: 0.37, range: 16, elapsed: 0, remaining: duration, duration,
    hits: 0, health: 3, message: 'ENTER THE ARENA', phaseAt: 0, startedAt: 0,
    flashUntil: 0, beamAt: -Infinity, danger: 0, phaseElapsed: 0 };
  let lastAt = 0;

  function lockAim() {
    const dx = hero.position.x - state.position.x, dz = hero.position.z - state.position.z;
    const length = Math.hypot(dx, dz) || 1;
    state.aim = { x: dx / length, z: dz / length };
  }
  function insideCone() {
    const dx = hero.position.x - state.position.x, dz = hero.position.z - state.position.z;
    const distance = Math.hypot(dx, dz);
    if (distance > state.range) return false;
    if (distance < 0.001) return true;
    return (dx * state.aim.x + dz * state.aim.z) / distance >= Math.cos(state.halfAngle);
  }
  function reset() {
    Object.assign(state, { phase: 'idle', position: { ...position }, aim: { x: 0, z: 1 },
      elapsed: 0, remaining: duration, hits: 0, health: 3, message: 'ENTER THE ARENA',
      phaseAt: 0, startedAt: 0, flashUntil: 0, beamAt: -Infinity, danger: 0, phaseElapsed: 0 });
    lastAt = 0;
  }
  function start(now) {
    reset(); state.phase = 'warning'; state.message = 'BOSS AWAKENED';
    state.startedAt = now; state.phaseAt = now; lastAt = now; lockAim();
  }
  function update(now, frameDt) {
    if (state.phase === 'idle' || state.phase === 'defeat' || state.phase === 'victory') return;
    const dt = Math.max(0, Math.min(0.05, frameDt ?? now - lastAt));
    lastAt = now;
    state.elapsed = Math.min(duration, state.elapsed + dt);
    state.remaining = Math.max(0, duration - state.elapsed);
    if (state.elapsed >= duration) { state.phase = 'victory'; state.message = 'YOU SURVIVED'; return; }
    state.phaseElapsed += dt;
    if (state.phase === 'warning' && state.phaseElapsed >= warning - 1e-8) {
      state.phase = 'laser'; state.phaseAt = now; state.phaseElapsed = 0; state.beamAt = now;
      if (insideCone()) {
        state.hits++; state.health = 3 - state.hits; state.flashUntil = now + 0.35;
        state.message = state.health ? 'LASER HIT!' : 'LENNY FALLS';
        if (!state.health) state.phase = 'defeat';
      } else state.message = 'DODGED!';
    } else if (state.phase === 'laser' && state.phaseElapsed >= laser - 1e-8) {
      state.phase = 'recover'; state.phaseAt = now; state.phaseElapsed = 0;
    } else if (state.phase === 'recover') {
      if (state.phaseElapsed >= recover - 1e-8) {
        state.phase = 'warning'; state.phaseAt = now; state.phaseElapsed = 0; state.message = 'INCOMING'; lockAim();
      } else {
        const dx = hero.position.x - state.position.x, dz = hero.position.z - state.position.z;
        const distance = Math.hypot(dx, dz);
        if (distance > 1.85) {
          const step = Math.min(distance - 1.85, (1.25 + state.elapsed / duration * 0.55) * dt);
          state.position.x += dx / distance * step;
          state.position.z += dz / distance * step;
          state.position.x = Math.max(room.minX + 0.65, Math.min(room.maxX - 0.65, state.position.x));
          state.position.z = Math.max(room.minZ + 0.65, Math.min(room.maxZ - 0.65, state.position.z));
        }
      }
    }
    const distance = Math.hypot(hero.position.x - state.position.x, hero.position.z - state.position.z);
    state.danger = Math.max(0, Math.min(1, 1 - (distance - 1.5) / 5));
  }
  return { state, start, reset, update };
}
