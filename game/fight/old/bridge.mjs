// bridge.mjs: pure logic for the "Rope Bridge" balance level. No DOM, no canvas,
// no input devices — debug.html feeds it `input = { v, u, handActive, requireHand }`
// already derived from the SAME gesture/keyboard/easing pipeline every other level
// uses (see debug.html's heroVel/easeVelocity/gestureTargetVel, unchanged).
//
// Local coordinates only: u = along the bridge (0 = start, LENGTH = goal),
// v = across the bridge (0 = center). Rendering (bridge_view.mjs) maps (u,v) to
// world/canvas space through VIEW_ROT; this file never sees that.

function mulberry32(seed) {
  let a = seed >>> 0;
  return function rng() {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const lerp = (a, b, t) => a + (b - a) * Math.min(1, Math.max(0, t));
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));

// NOTE on tuning: HALF_WIDTH, SWAY.amp*, and GUSTS.gap* were widened from this
// task's stated starting values (2.2 / 0.10-0.30 / lerp(2.0,1.0,p)s) during the
// bridge.sim.mjs acceptance pass -- see bridge.sim.mjs's header comment and the
// Phase 1 report for the bot table these numbers were tuned against.
export const DEFAULTS = {
  THEME: 'bright', // 'bright' (lit white board) | 'dark' (black surface)
  HALF_WIDTH: 2.8, // bridge width 5.6 units
  CROSS_TIME: 24, // seconds of walking at the auto forward speed
  FORWARD_MODE: 'auto', // 'auto' | 'manual'
  INTRO: 3, // seconds, no drift and no walking
  SWAY: { ampMin: 0.13, ampMax: 0.39, period: 5.5, periodJitter: 0.20 },
  GUSTS: {
    telegraph: 0.9, rampUp: 0.35, holdMin: 0.9, holdMax: 1.6, rampDown: 0.5,
    gmaxMin: 0.40, gmaxMax: 0.80, strengthMin: 0.6, strengthMax: 1.0,
    gapMin: 1.2, gapMax: 2.4, gapJitter: 0.25,
  },
  DRIFT_CLAMP: 0.90, // * HERO_LAT_SPEED; so a full opposite input always wins
  EDGE_MARGIN: 0.10, // |v| beyond HALF_WIDTH - this = over the edge
  EDGE_GRACE: 0.15, // seconds of overhang allowed before it's a fall
  FALL_DURATION: 0.7,
  RESPAWN_HOLD: 1.2,
  HAND_LOSS_TIMEOUT: 0.8,
  HAND_REGAIN: 0.5,
  CALM_RAMP: 1.0, // seconds to ramp drift back in after a hand-loss pause
  CHECKPOINTS: [0, 0.33, 0.66], // progress fractions
  MANUAL_FORWARD_MULT: 1.6,
  gustScale: 1.0, // live-tunable (7/8 keys), multiplies gust strength
};

function mergeConfig(config) {
  const c = { ...DEFAULTS, ...config };
  c.SWAY = { ...DEFAULTS.SWAY, ...(config && config.SWAY) };
  c.GUSTS = { ...DEFAULTS.GUSTS, ...(config && config.GUSTS) };
  if (!Number.isFinite(c.LENGTH) || c.LENGTH <= 0) {
    throw new Error('bridge.mjs: config.LENGTH is required (computed by the caller from the arena + VIEW_ROT)');
  }
  if (!Number.isFinite(c.HERO_LAT_SPEED) || c.HERO_LAT_SPEED <= 0) {
    throw new Error('bridge.mjs: config.HERO_LAT_SPEED is required (the existing hero speed, e.g. 3.0)');
  }
  return c;
}

// Schedules the next gust: direction, peak strength (gmax(p) * random factor),
// and the gap before it starts telegraphing. p is progress (0..1) at schedule time.
function scheduleGust(state, rng) {
  const g = state.config.GUSTS;
  const p = clamp(state.u / state.config.LENGTH, 0, 1);
  const gmax = lerp(g.gmaxMin, g.gmaxMax, p) * state.config.HERO_LAT_SPEED;
  const strength = gmax * lerp(g.strengthMin, g.strengthMax, rng());
  const gap = lerp(g.gapMax, g.gapMin, p) * (1 + (rng() * 2 - 1) * g.gapJitter);
  state.nextGustAt = state.t + Math.max(0.1, gap);
  state.nextGustDir = rng() < 0.5 ? -1 : 1;
  state.nextGustStrength = strength;
}

function nearestCheckpointAtOrBefore(config, p) {
  let best = 0;
  for (const cp of config.CHECKPOINTS) if (cp <= p + 1e-9) best = Math.max(best, cp);
  return best;
}

export function createBridge(config, seed) {
  const merged = mergeConfig(config);
  const rng = mulberry32(seed >>> 0);
  const periodJitterSign = rng() * 2 - 1;
  const state = {
    config: merged, seed: seed >>> 0, rng,
    phase: 'INTRO', paused: false,
    t: 0, u: 0, v: 0,
    introT: 0,
    swayPeriod: merged.SWAY.period * (1 + periodJitterSign * merged.SWAY.periodJitter),
    swayPhase: rng() * Math.PI * 2,
    gust: null, // { dir, strength, startedAt, stage } while a gust is telegraphing/active
    nextGustAt: merged.INTRO, nextGustDir: 1, nextGustStrength: 0,
    overEdgeT: 0, // how long |v| has been past the edge margin
    fallT: 0,
    respawnHoldT: 0,
    checkpoint: 0, // furthest progress fraction reached, respawn target
    falls: 0,
    noHandT: 0, handActiveT: 0, calmRampT: 0, // hand-loss tracking
    forwardMode: merged.FORWARD_MODE,
    viewRot: 90, // caller-owned display value, kept here only so the HUD/log has one source of truth
  };
  scheduleGust(state, rng);
  return state;
}

// Current gust drift contribution at time `t`, given the scheduled/active gust.
// Returns { value, dir, gustActive, telegraphing, timeIntoTelegraph } for drawing + bots.
function gustDrift(state) {
  const g = state.config.GUSTS;
  const until = (stage) => stage === 'telegraph' ? g.telegraph
    : stage === 'rampUp' ? g.telegraph + g.rampUp
    : stage === 'hold' ? g.telegraph + g.rampUp + state.gust.holdDur
    : g.telegraph + g.rampUp + state.gust.holdDur + g.rampDown;
  if (!state.gust) return { value: 0, dir: state.nextGustDir, gustActive: false, telegraphing: false, timeIntoTelegraph: 0 };
  const dt = state.t - state.gust.startedAt;
  const tEnd = until('rampDown');
  if (dt >= tEnd) return { value: 0, dir: state.gust.dir, gustActive: false, telegraphing: false, timeIntoTelegraph: 0 };
  const scale = state.config.gustScale ?? 1;
  if (dt < g.telegraph) return { value: 0, dir: state.gust.dir, gustActive: false, telegraphing: true, timeIntoTelegraph: dt };
  const rampUpEnd = g.telegraph + g.rampUp, holdEnd = rampUpEnd + state.gust.holdDur;
  let frac;
  if (dt < rampUpEnd) frac = (dt - g.telegraph) / g.rampUp;
  else if (dt < holdEnd) frac = 1;
  else frac = 1 - (dt - holdEnd) / g.rampDown;
  return { value: state.gust.dir * state.gust.strength * scale * clamp(frac, 0, 1), dir: state.gust.dir, gustActive: true, telegraphing: false, timeIntoTelegraph: 0 };
}

function swayAt(state) {
  const c = state.config;
  const p = clamp(state.u / c.LENGTH, 0, 1);
  const amp = lerp(c.SWAY.ampMin, c.SWAY.ampMax, p) * c.HERO_LAT_SPEED;
  return amp * Math.sin((2 * Math.PI * state.t) / state.swayPeriod + state.swayPhase);
}

// Total instantaneous drift (sway + gust), clamped the same way step() applies
// it (minus the calm-ramp multiplier, which only matters right at hand-loss
// resume). This is what a player actually feels right now -- bots react to
// THIS, not the gust alone, since sway and a gust can stack in either direction.
function driftAt(state) {
  const c = state.config;
  const gd = gustDrift(state);
  const sway = swayAt(state);
  const driftClamp = c.DRIFT_CLAMP * c.HERO_LAT_SPEED;
  const total = clamp(sway + gd.value, -driftClamp, driftClamp);
  return { total, sway, gust: gd.value, dir: gd.dir, gustActive: gd.gustActive, telegraphing: gd.telegraphing, timeIntoTelegraph: gd.timeIntoTelegraph };
}

// Advances `state` by `dt` seconds given `input = { v, u, handActive, requireHand }`.
// v/u are already-eased world-units/sec signals from the existing pipeline (see
// debug.html: input.v = heroVel.x, input.u = -heroVel.z in manual FORWARD_MODE).
export function step(state, dt, input) {
  const c = state.config;
  state.t += dt;

  // Hand-loss pause: freezes walking, sway, gusts and fall timers. PAUSED is an
  // overlay on top of `phase`, not a phase of its own.
  const handActive = !!(input && input.handActive);
  const requireHand = !input || input.requireHand !== false;
  if (handActive) { state.handActiveT += dt; state.noHandT = 0; } else { state.noHandT += dt; state.handActiveT = 0; }
  if (requireHand) {
    if (!state.paused && state.noHandT > c.HAND_LOSS_TIMEOUT) { state.paused = true; state.calmRampT = 0; }
    else if (state.paused && state.handActiveT > c.HAND_REGAIN) { state.paused = false; state.calmRampT = 0; }
  } else if (state.paused) {
    state.paused = false; state.calmRampT = 0;
  }
  if (state.paused) return state; // fully frozen while paused

  const vIn = (input && Number.isFinite(input.v)) ? input.v : 0;
  const uIn = (input && Number.isFinite(input.u)) ? input.u : 0;

  if (state.phase === 'INTRO') {
    state.introT += dt;
    if (state.introT >= c.INTRO) { state.phase = 'CROSSING'; state.nextGustAt = state.t + c.GUSTS.telegraph; }
    return state; // no drift, no walking during intro (this task's stated default)
  }

  if (state.phase === 'FALLING') {
    state.fallT += dt;
    if (state.fallT >= c.FALL_DURATION) {
      state.phase = 'RESPAWN_HOLD'; state.respawnHoldT = 0;
      state.u = state.checkpoint * c.LENGTH; state.v = 0;
    }
    return state;
  }
  if (state.phase === 'RESPAWN_HOLD') {
    state.respawnHoldT += dt;
    if (state.respawnHoldT >= c.RESPAWN_HOLD) state.phase = 'CROSSING';
    return state;
  }
  if (state.phase === 'CLEARED') return state;

  // CROSSING
  state.calmRampT += dt;
  const calm = clamp(state.calmRampT / c.CALM_RAMP, 0, 1);

  // forward progress
  const autoSpeed = c.LENGTH / c.CROSS_TIME;
  let forwardSpeed;
  if (state.forwardMode === 'manual') forwardSpeed = uIn > 1e-3 ? autoSpeed * c.MANUAL_FORWARD_MULT : 0;
  else forwardSpeed = autoSpeed;
  state.u = clamp(state.u + forwardSpeed * dt, 0, c.LENGTH);

  const p = clamp(state.u / c.LENGTH, 0, 1);
  for (const cp of c.CHECKPOINTS) if (p >= cp - 1e-9) state.checkpoint = Math.max(state.checkpoint, cp);

  // gusts: advance the schedule, start one when due
  if (!state.gust && state.t >= state.nextGustAt) {
    state.gust = { dir: state.nextGustDir, strength: state.nextGustStrength, startedAt: state.t, holdDur: lerp(c.GUSTS.holdMin, c.GUSTS.holdMax, state.rng()) };
  }
  const gd = gustDrift(state);
  if (state.gust && !gd.gustActive && !gd.telegraphing) { state.gust = null; scheduleGust(state, state.rng); }

  const drift = driftAt(state).total * calm; // calm ramp softens drift right after a hand-loss resume

  state.v += (vIn + drift) * dt;

  // edge fall rule
  const edge = c.HALF_WIDTH - c.EDGE_MARGIN;
  if (Math.abs(state.v) > edge) state.overEdgeT += dt; else state.overEdgeT = 0;
  if (state.overEdgeT > c.EDGE_GRACE) {
    state.phase = 'FALLING'; state.fallT = 0; state.falls += 1; state.overEdgeT = 0;
  }

  if (state.u >= c.LENGTH - 1e-6) state.phase = 'CLEARED';
  return state;
}

export function gustInfo(state) { return gustDrift(state); }
export function driftInfo(state) { return driftAt(state); }
export { mulberry32, clamp, lerp };
