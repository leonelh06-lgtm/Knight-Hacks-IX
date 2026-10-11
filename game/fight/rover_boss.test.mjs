import test from 'node:test';import assert from 'node:assert/strict';
import {createRoverBoss,toBoardPlayer,roverEligible} from './rover_boss.mjs';
import {createRoverClient} from './rover_client.mjs';
const calibration={calibration_id:'c',verified:true,arena:{x_mm:50,y_mm:20,width_mm:800,height_mm:450},projection_size:[1600,900]};
test('mapping uses authoritative final position and conservative radius',()=>{
 const room={minX:-8,maxX:8,minZ:-1,maxZ:8};
 assert.deepEqual(toBoardPlayer({position:{x:0,z:3.5}},room,calibration.arena,.3),{x_mm:450,y_mm:245,radius_mm:15});
 assert.equal(toBoardPlayer({position:{x:-8,z:-1}},room,calibration.arena,.3).x_mm,50);
});
test('eligibility covers exits, terminal, visibility, pause and projection changes',()=>{
 const state={physicalBoss:true,started:true,terminal:false,paused:false,visible:true,projectionSize:[1600,900]};
 assert.equal(roverEligible(state,calibration),true);
 for(const override of [{physicalBoss:false},{started:false},{terminal:true},{paused:true},{visible:false},{projectionSize:[900,1600]},{projectionInvalid:true}])
  assert.equal(roverEligible({...state,...override},calibration),false);
 assert.equal(roverEligible(state,null),false);
});
test('contact policy deduplicates and checks encounter/calibration',()=>{
 let defeats=0;const boss=createRoverBoss({onDefeat:()=>defeats++});boss.reset('s','c');
 const event={session_id:'s',calibration_id:'c',event_id:'e'};
 assert.equal(boss.handleContact({...event,session_id:'old'}),false);
 assert.equal(boss.handleContact({...event,calibration_id:'old'}),false);
 assert.equal(boss.handleContact(event),true);assert.equal(boss.handleContact(event),true);assert.equal(defeats,1);assert.equal(boss.terminal,true);
 let hits=0;const alternate=createRoverBoss({policy:()=>hits++});alternate.reset('s','c');alternate.handleContact(event);assert.equal(hits,1);assert.equal(alternate.terminal,false);
});
class Socket {
 constructor(){this.readyState=1;this.sent=[];this.listeners=new Map();}
 send(x){this.sent.push(JSON.parse(x));}
 addEventListener(k,fn){this.listeners.set(k,fn);}
 removeEventListener(k){this.listeners.delete(k);}
 message(m){this.listeners.get('message')({data:JSON.stringify(m)});}
}
test('client claims ownership, waits for ack, emits validated state and contact acknowledgments',()=>{
 const socket=new Socket();let contacts=0;const client=createRoverClient({socket,sessionId:'s',calibration,onContact:()=>{contacts++;return true;}});
 assert.equal(socket.sent[0].type,'claim_game');
 const state={level_id:'boss-arena',physical_boss:true,active:true,terminal:false,player:{x_mm:450,y_mm:245,radius_mm:15}};
 assert.equal(client.publishGame(state),false);socket.message({type:'game_claimed',session_id:'s'});assert.equal(client.publishGame(state),true);
 const event={type:'rover_contact',version:1,session_id:'s',calibration_id:'c',event_id:'e',level_id:'boss-arena'};
 socket.message(event);assert.equal(contacts,1);assert.equal(socket.sent.at(-1).type,'contact_ack');
 socket.message({...event,session_id:'old'});assert.equal(contacts,1);
 client.close();assert.equal(socket.sent.at(-1).active,false);
});
