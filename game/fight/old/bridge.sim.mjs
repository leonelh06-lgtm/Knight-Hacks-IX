// bridge.sim.mjs: headless acceptance test for the Rope Bridge level (bridge.mjs).
// Run: node bridge.sim.mjs
//
// These bots are NOT a model of real players -- they're simple reaction/delay
// automatons used only to sanity-check that the DEFAULTS config is "strong
// enough to be fun, never impossible" across a spread of skill levels. A real
// human reacts to light/sound/motion on the rendered bridge, not to internal
// state; these bots read bridge.mjs's driftInfo() directly (with an imposed
// delay) as a stand-in for "noticing the telegraph" and "feeling the push."
//
// Bot model: continuous proportional control on a DELAYED observation of v
// (this alone creates the sway-handling degradation with reaction delay --
// classic delayed-feedback control, no ad-hoc dead zones needed) plus a
// feedforward "lean" toward the gust direction once the delayed telegraph
// signal is perceived, rate-limited by switchDelay (a slew rate modeling how
// fast a player commits to a new direction, not a hard switch gate).
import { createBridge, step, driftInfo, DEFAULTS } from './bridge.mjs';

const LENGTH = 16; // representative of (room width - 1.6) at a 16:9 projector, VIEW_ROT=90
const HERO_LAT_SPEED = 3.0;
const FULL_STRENGTH = HERO_LAT_SPEED; // a player's max steering input, same cap the live pipeline has
const DT = 1 / 60;
const MAX_SIM_SECONDS = 600; // generous safety cutoff (25x CROSS_TIME); a non-clear by then counts as a timeout
const KP = 2.2, LEAN_STRENGTH = 2.6;

function makeBot({ reactDelay, switchDelay }) {
  return () => ({
    history: [], lean: 0,
    decide(state, dt) {
      const d = driftInfo(state);
      this.history.push({ t: state.t, v: state.v, dir: d.dir, active: d.telegraphing || d.gustActive });
      while (this.history.length > 2 && this.history[1].t < state.t - reactDelay - 1) this.history.shift();
      let perceived = this.history[0];
      for (const h of this.history) if (h.t <= state.t - reactDelay) perceived = h; else break;

      const leanTarget = perceived.active ? (perceived.dir > 0 ? -1 : 1) : 0;
      const maxRate = switchDelay > 0 ? 1 / switchDelay : 1e6;
      this.lean += Math.max(-maxRate * dt, Math.min(maxRate * dt, leanTarget - this.lean));

      const out = -KP * perceived.v + this.lean * LEAN_STRENGTH;
      return Math.max(-FULL_STRENGTH, Math.min(FULL_STRENGTH, out));
    },
  });
}

const BOTS = {
  PERFECT: { make: makeBot({ reactDelay: 0.15, switchDelay: 0 }), target: 'clean>=0.99' },
  LAGGED: { make: makeBot({ reactDelay: 0.35, switchDelay: 0.40 }), target: 'clean>=0.85, <=2falls>=0.99' },
  SLOPPY: { make: makeBot({ reactDelay: 0.8, switchDelay: 0.7 }), target: 'clean in [0.15,0.60]' },
  ZERO_INPUT: { make: () => ({ decide: () => 0 }), target: '>=1 fall in >=0.95' },
};

function runOne(botFactory, seed) {
  const state = createBridge({ LENGTH, HERO_LAT_SPEED, FORWARD_MODE: 'auto' }, seed);
  const bot = botFactory();
  let t = 0;
  while (state.phase !== 'CLEARED' && t < MAX_SIM_SECONDS) {
    const v = bot.decide(state, DT);
    step(state, DT, { v, u: 0, handActive: true, requireHand: true });
    t += DT;
  }
  return { cleared: state.phase === 'CLEARED', falls: state.falls, timeout: t >= MAX_SIM_SECONDS };
}

function runBot(name, { make }, seeds) {
  let cleared = 0, cleanClear = 0, within2 = 0, anyFall = 0, timeouts = 0;
  for (let s = 0; s < seeds; s++) {
    const r = runOne(make, s * 7919 + 13); // spread seeds, avoid trivial correlation with bot loop index
    if (r.cleared) { cleared++; if (r.falls === 0) cleanClear++; if (r.falls <= 2) within2++; }
    if (r.falls > 0) anyFall++;
    if (r.timeout) timeouts++;
  }
  return {
    name, seeds, cleared: cleared / seeds, cleanClear: cleanClear / seeds,
    within2: within2 / seeds, anyFall: anyFall / seeds, timeouts,
  };
}

function checkTargets(r) {
  if (r.name === 'PERFECT') return r.cleanClear >= 0.99;
  if (r.name === 'LAGGED') return r.cleanClear >= 0.85 && r.within2 >= 0.99;
  if (r.name === 'SLOPPY') return r.cleanClear >= 0.15 && r.cleanClear <= 0.60;
  if (r.name === 'ZERO_INPUT') return r.anyFall >= 0.95;
  return false;
}

export function runAcceptance(seeds = 500) {
  return Object.entries(BOTS).map(([name, bot]) => runBot(name, bot, seeds));
}

if (process.argv[1] && process.argv[1].endsWith('bridge.sim.mjs')) {
  const results = runAcceptance(500);
  console.log(`DEFAULTS (tuned): HALF_WIDTH=${DEFAULTS.HALF_WIDTH} GUSTS.gmax=[${DEFAULTS.GUSTS.gmaxMin},${DEFAULTS.GUSTS.gmaxMax}] GUSTS.gap=[${DEFAULTS.GUSTS.gapMin},${DEFAULTS.GUSTS.gapMax}]s SWAY.amp=[${DEFAULTS.SWAY.ampMin},${DEFAULTS.SWAY.ampMax}] DRIFT_CLAMP=${DEFAULTS.DRIFT_CLAMP} | LENGTH=${LENGTH} CROSS_TIME=${DEFAULTS.CROSS_TIME}`);
  console.log('bot'.padEnd(12), 'cleared'.padEnd(9), 'cleanClear'.padEnd(11), 'within2falls'.padEnd(13), 'anyFall'.padEnd(9), 'timeouts', 'target', 'pass');
  let allPass = true;
  for (const r of results) {
    const pass = checkTargets(r);
    allPass = allPass && pass;
    console.log(
      r.name.padEnd(12),
      (r.cleared * 100).toFixed(1).padEnd(9),
      (r.cleanClear * 100).toFixed(1).padEnd(11),
      (r.within2 * 100).toFixed(1).padEnd(13),
      (r.anyFall * 100).toFixed(1).padEnd(9),
      String(r.timeouts).padEnd(8),
      BOTS[r.name].target,
      pass ? 'PASS' : 'FAIL',
    );
  }
  if (!allPass) { console.error('bridge.sim.mjs: one or more bots missed their target -- tune DEFAULTS and re-run.'); process.exit(1); }
  console.log('bridge.sim.mjs: all bots within target ranges.');
}
