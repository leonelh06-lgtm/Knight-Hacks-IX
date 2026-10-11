import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {validateRoverMessage} from './rover_protocol.mjs';
const rows=JSON.parse(fs.readFileSync(new URL('../../tests/fixtures/rover_messages.json',import.meta.url)));
test('shared wire fixtures',()=>{for(const r of rows){if(r.valid)assert.deepEqual(validateRoverMessage(r.message),r.message);else assert.throws(()=>validateRoverMessage(r.message));}});
test('nonfinite and boolean coordinates rejected',()=>{for(const v of [NaN,Infinity,true]) {const m=structuredClone(rows[0].message);m.player.x_mm=v;assert.throws(()=>validateRoverMessage(m));}});
