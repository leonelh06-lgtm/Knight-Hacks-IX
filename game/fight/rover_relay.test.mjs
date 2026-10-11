import {test} from 'node:test';import assert from 'node:assert/strict';import dgram from 'node:dgram';import {EventEmitter,once} from 'node:events';import fs from 'node:fs';import {createRoverRelay} from './rover_relay.mjs';
const state=JSON.parse(fs.readFileSync(new URL('../../tests/fixtures/rover_messages.json',import.meta.url)))[0].message;
test('owner routing, second-tab rejection, telemetry and disconnect stop',async()=>{
 const target=dgram.createSocket('udp4');target.bind(0,'127.0.0.1');await once(target,'listening');
 const wss=new EventEmitter();const r=createRoverRelay({wss,gameStatePort:target.address().port,roverStatePort:0});await r.ready;
 const client=()=>Object.assign(new EventEmitter(),{readyState:1,messages:[],send(s){this.messages.push(JSON.parse(s));}});
 const a=client(),b=client();wss.emit('connection',a);wss.emit('connection',b);
 try{
  assert.equal(r.handleMessage(a,{type:'claim_game',version:1,session_id:'test'}),true);
  assert.equal(r.handleMessage(b,{type:'claim_game',version:1,session_id:'other'}),false);
  const got=once(target,'message');assert(r.handleMessage(a,state));assert.deepEqual(JSON.parse((await got)[0]),state);
  assert.equal(r.handleMessage(b,{...state,seq:2}),false);assert.equal(r.handleMessage(a,state),false);
  const pose=JSON.parse(fs.readFileSync(new URL('../../tests/fixtures/rover_messages.json',import.meta.url)))[1].message;
  const sender=dgram.createSocket('udp4');sender.send(JSON.stringify(pose),r.address().port,'127.0.0.1');
  await new Promise(resolve=>setTimeout(resolve,40));sender.close();assert(a.messages.some(m=>m.type==='rover_state'));
  const stop=once(target,'message');a.emit('close');assert.equal(JSON.parse((await stop)[0]).active,false);
  assert(r.handleMessage(b,{type:'claim_game',version:1,session_id:'other'}));
 }finally{await r.close();target.close();}
});
