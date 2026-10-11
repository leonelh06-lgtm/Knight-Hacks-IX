// predictor.test.mjs, run with: node predictor.test.mjs
import assert from 'node:assert';
import { DodgePredictor } from './predictor.mjs';

const aim = { x: 1, y: 0 }, p0 = { x: 0, y: 0 };
const side = (s) => ({ x: 0, y: s }); // dodge sideways by s units

let p = new DodgePredictor();
for (let i = 0; i < 5; i++) p.observe(p0, side(1), aim);
assert.equal(p.predict().dir, 'PLUS');
assert(p.predict().confidence > 0.7);       // always one way: confident

p = new DodgePredictor();
for (let i = 0; i < 6; i++) p.observe(p0, side(i % 2 ? 1 : -1), aim);
assert(p.predict().confidence < 0.6);       // alternating: should NOT be confident

p = new DodgePredictor();
for (let i = 0; i < 5; i++) p.observe(p0, side(1), aim);
for (let i = 0; i < 3; i++) p.observe(p0, side(-1), aim);
assert.equal(p.predict().dir, 'MINUS');     // habit changes: it should adapt
console.log('predictor tests passed');
