// fight.js (untested). Produces the `fight` object that createBossEffects reads.
export function createFight(config, hero, { chooseAim, onResolve } = {}) {
  const T = { warning: 1.0, laser: 0.4, recover: 2.0, shieldFor: 0.6, shieldCooldown: 2.5, damage: 25, dashFor: 0.2, dashCooldown: 1.5 };
  const f = { config, boss: { x: config.position.x, z: config.position.z } };
  let shieldReadyAt = 0, phaseAt = 0, p0 = null;

  function reset() {
    Object.assign(f, {
      phase: 'idle', aim: { x: 0, z: 1 }, firedAt: -1e9, shieldUntil: 0,
      counterAt: null, counterFrom: { x: 0, z: 0 }, victoryAt: 0, flashUntil: 0,
      playerHP: 100, bossHP: 3, message: 'Press B to start',
      dashUntil: 0, dashReadyAt: 0,
    });
    shieldReadyAt = 0;
  }
  const inCone = (p) => {
    const dx = p.x - f.boss.x, dz = p.z - f.boss.z, d = Math.hypot(dx, dz);
    if (d > config.range) return false;
    if (d < 1e-6) return true;
    const cos = Math.max(-1, Math.min(1, (dx * f.aim.x + dz * f.aim.z) / d));
    return Math.acos(cos) <= config.halfAngle;
  };
  function lockAim() {
    p0 = { x: hero.position.x, z: hero.position.z };
    let a = chooseAim ? chooseAim(f.boss, p0) : null;           // predictor hook
    if (!a) { const dx = p0.x - f.boss.x, dz = p0.z - f.boss.z, d = Math.hypot(dx, dz) || 1; a = { x: dx / d, z: dz / d }; }
    f.aim = a;
  }
  function start(now) { reset(); f.phase = 'warning'; f.message = 'BOSS AWAKENED'; phaseAt = now; lockAim(); }
  function shield(now) {
    if (f.phase === 'idle' || now < shieldReadyAt) return;
    f.shieldUntil = now + T.shieldFor; shieldReadyAt = now + T.shieldCooldown;
  }
  function dash(now) {
    if (f.phase === 'idle' || now < f.dashReadyAt) return;
    f.dashUntil = now + T.dashFor; f.dashReadyAt = now + T.dashCooldown;
  }
  function update(now) {
    if (f.counterAt !== null && now >= f.counterAt) {              // counter lands
      f.counterAt = null; f.bossHP -= 1;
      if (f.bossHP <= 0) { f.phase = 'victory'; f.victoryAt = now; f.message = 'BOSS DEFEATED'; return; }
    }
    if (f.phase === 'warning' && now - phaseAt >= T.warning) {      // fire, resolve the hit now
      f.phase = 'laser'; phaseAt = now; f.firedAt = now;
      const p1 = { x: hero.position.x, z: hero.position.z };
      const blocked = now < f.shieldUntil, dashed = now < f.dashUntil;
      const hit = !blocked && !dashed && inCone(p1);
      if (hit) { f.playerHP = Math.max(0, f.playerHP - T.damage); f.flashUntil = now + 0.35; f.message = 'HIT!'; }
      else { f.message = dashed ? 'DASHED!' : (blocked ? 'BLOCKED!' : 'DODGED!'); f.counterFrom = { ...p1 }; f.counterAt = now + config.counter; }
      onResolve?.({ t: now, boss: { ...f.boss }, p0, p1, aim: { ...f.aim }, hit, blocked });
      if (f.playerHP <= 0) { f.phase = 'defeat'; f.message = 'DEFEATED'; }
    } else if (f.phase === 'laser' && now - phaseAt >= T.laser) { f.phase = 'recover'; phaseAt = now; }
    else if (f.phase === 'recover' && now - phaseAt >= T.recover) { f.phase = 'warning'; phaseAt = now; f.message = 'INCOMING'; lockAim(); }
  }
  reset();
  return { state: f, start, reset, shield, dash, update };
}
