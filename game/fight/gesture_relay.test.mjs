import test from 'node:test';import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';import {once} from 'node:events';import dgram from 'node:dgram';
import {WebSocket} from 'ws';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function freePort(){const s=dgram.createSocket('udp4');s.bind(0,'127.0.0.1');await once(s,'listening');const p=s.address().port;s.close();return p;}
test('existing headless gesture controller still reaches browser through actual relay', {timeout:15000},async()=>{
 const udpPort=await freePort();
 const net=await import('node:net');const holder=net.createServer();holder.listen(0,'127.0.0.1');await once(holder,'listening');const wsPort=holder.address().port;await new Promise(r=>holder.close(r));
 const relay=spawn(process.execPath,['game/fight/relay.mjs'],{env:{...process.env,UDP_PORT:String(udpPort),WS_PORT:String(wsPort)}});
 let logs='';relay.stdout.on('data',x=>logs+=x);relay.stderr.on('data',x=>logs+=x);
 let ws;
 try {
  const deadline=Date.now()+4000;while(!logs.includes('relay: udp')&&Date.now()<deadline){if(relay.exitCode!==null)throw new Error(logs);await sleep(20);}
  assert.match(logs,/relay: udp/);
  ws=new WebSocket('ws://127.0.0.1:'+wsPort);await once(ws,'open');const messages=[];ws.on('message',x=>messages.push(JSON.parse(x)));
  const hand=spawn(process.env.GESTURE_TEST_PYTHON||'python',['-u','-m','gesture_control','--headless','--simulate','--frames','6','--udp-port',String(udpPort)]);
  let errors='';hand.stderr.on('data',x=>errors+=x);hand.stdout.resume();await once(hand,'exit');assert.equal(hand.exitCode,0,errors);await sleep(50);
  assert.ok(messages.some(m=>m.active&&m.vy===-1));assert.equal(messages.at(-1).active,false);
 } finally {ws?.terminate();relay.kill();if(relay.exitCode===null)await once(relay,'exit');}
});
