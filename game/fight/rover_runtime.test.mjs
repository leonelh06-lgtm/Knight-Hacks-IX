import test from 'node:test';import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';import {once} from 'node:events';import dgram from 'node:dgram';
import {WebSocketServer,WebSocket} from 'ws';
import {createRoverRelay} from './rover_relay.mjs';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function freePort(){const s=dgram.createSocket('udp4');s.bind(0,'127.0.0.1');await once(s,'listening');const p=s.address().port;s.close();return p;}
test('real WebSocket/UDP -> Python runtime -> fake BLE; stale camera stops and contact reaches browser', {timeout:15000},async()=>{
 const gamePort=await freePort();
 const wss=new WebSocketServer({port:0});await once(wss,'listening');
 const relay=createRoverRelay({wss,gameStatePort:gamePort,roverStatePort:0});await relay.ready;
 const child=spawn(process.env.ROVER_TEST_PYTHON||'python',['-u','tests/fixtures/rover_runtime.py',String(gamePort),String(relay.address().port)],{stdio:['pipe','pipe','pipe']});
 let output='',errors='';child.stdout.on('data',x=>output+=x);child.stderr.on('data',x=>errors+=x);
 const ws=new WebSocket('ws://127.0.0.1:'+wss.address().port);let phase=0,contacts=0,states=[],seq=0,interval;
 const state={type:'game_state',version:1,session_id:'integration',calibration_id:'c',level_id:'boss-arena',physical_boss:true,active:true,terminal:false,arena:{x_mm:0,y_mm:0,width_mm:914.4,height_mm:508},player:{x_mm:700,y_mm:254,radius_mm:10}};
 const sendState=()=>ws.send(JSON.stringify({...state,seq:seq++}));
 try {
  await once(ws,'open');
  ws.on('message',raw=>{
   const m=JSON.parse(raw);
   if(m.type==='game_claimed'){interval=setInterval(sendState,50);sendState();}
   if(m.type==='rover_state'){
    states.push(m);
    if(phase===0&&m.valid){assert.equal(m.armed,false);phase=1;child.stdin.write('g\n');}
    else if(phase===1&&m.armed&&output.includes('MOCK MOTOR W')){phase=2;child.stdin.write('stall\n');}
    else if(phase===2&&m.status==='tracking stale'){assert.equal(m.armed,false);phase=3;child.stdin.write('resume\n');}
    else if(phase===3&&m.valid){assert.equal(m.armed,false);phase=4;child.stdin.write('g\n');}
    else if(phase===4&&m.armed&&(output.match(/MOCK MOTOR W/g)||[]).length>=2){phase=5;child.stdin.write('contact\n');}
   }
   if(m.type==='rover_contact'){
    contacts++;phase=6;
    ws.send(JSON.stringify({type:'contact_ack',version:1,session_id:m.session_id,calibration_id:m.calibration_id,event_id:m.event_id}));
    state.active=false;state.terminal=true;sendState();
   }
  });
  ws.send(JSON.stringify({type:'claim_game',version:1,session_id:'integration'}));
  const deadline=Date.now()+7000;
  while(phase!==6&&Date.now()<deadline){if(child.exitCode!==null)throw new Error(output+errors);await sleep(20);}
  assert.equal(phase,6,output+errors);
  await sleep(100);assert.equal(contacts,1);child.stdin.write('q\n');
  await once(child,'exit');assert.equal(child.exitCode,0,errors);
  assert.match(output,/MOCK MOTOR W/);assert.match(output,/MOCK MOTOR X/);
  assert.ok(states.some(x=>x.status==='contact latched'));
 }finally {
  clearInterval(interval);ws.terminate();child.kill();
  await relay.close();await new Promise(r=>wss.close(r));
 }
});

test('existing headless gesture controller still reaches browser through actual relay', {timeout:15000},async()=>{
 const udpPort=await freePort(),gamePort=await freePort(),roverPort=await freePort();
 const net=await import('node:net');const holder=net.createServer();holder.listen(0,'127.0.0.1');await once(holder,'listening');const wsPort=holder.address().port;await new Promise(r=>holder.close(r));
 const relay=spawn(process.execPath,['game/fight/relay.mjs'],{env:{...process.env,UDP_PORT:String(udpPort),WS_PORT:String(wsPort),GAME_STATE_PORT:String(gamePort),ROVER_STATE_PORT:String(roverPort)}});
 let logs='';relay.stdout.on('data',x=>logs+=x);relay.stderr.on('data',x=>logs+=x);
 let ws;
 try {
  const deadline=Date.now()+4000;while(!logs.includes('relay: udp')&&Date.now()<deadline){if(relay.exitCode!==null)throw new Error(logs);await sleep(20);}
  assert.match(logs,/relay: udp/);
  ws=new WebSocket('ws://127.0.0.1:'+wsPort);await once(ws,'open');const messages=[];ws.on('message',x=>messages.push(JSON.parse(x)));
  const hand=spawn(process.env.ROVER_TEST_PYTHON||'python',['-u','-m','gesture_control','--headless','--simulate','--frames','6','--udp-port',String(udpPort)]);
  let errors='';hand.stderr.on('data',x=>errors+=x);hand.stdout.resume();await once(hand,'exit');assert.equal(hand.exitCode,0,errors);await sleep(50);
  assert.ok(messages.some(m=>m.active&&m.vy===-1));assert.equal(messages.at(-1).active,false);
 } finally {ws?.terminate();relay.kill();if(relay.exitCode===null)await once(relay,'exit');}
});
