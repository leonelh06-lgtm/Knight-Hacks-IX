import dgram from 'node:dgram';import {validateRoverMessage} from './rover_protocol.mjs';
export function createRoverRelay({wss,gameStatePort=8766,roverStatePort=8767}){
 const socket=dgram.createSocket('udp4');let owner=null,lastState=null,lastSeq=-1,closing=false;
 const send=m=>socket.send(JSON.stringify(m),gameStatePort,'127.0.0.1');
 const notify=(ws,m)=>{if(ws.readyState===1)ws.send(JSON.stringify(m));};
 const release=()=>{if(lastState)send({...lastState,seq:lastSeq+1,active:false});owner=null;lastState=null;lastSeq=-1;};
 const handleMessage=(ws,data)=>{
  let m;try{m=validateRoverMessage(typeof data==='object'&&!Buffer.isBuffer(data)?data:JSON.parse(String(data)));}catch{return false;}
  if(m.type==='claim_game'){
   if(owner&&owner.ws!==ws){notify(ws,{type:'game_claim_rejected',session_id:m.session_id});return false;}
   if(owner&&owner.session!==m.session_id)release();owner={ws,session:m.session_id};notify(ws,{type:'game_claimed',session_id:m.session_id});return true;
  }
  if(!owner||owner.ws!==ws||owner.session!==m.session_id)return false;
  if(m.type==='game_state'){
   if(m.seq<=lastSeq)return false;lastSeq=m.seq;lastState=m;send(m);return true;
  }
  if(m.type==='contact_ack'&&lastState&&m.calibration_id===lastState.calibration_id){send(m);return true;}
  return false;
 };
 wss.on('connection',ws=>{ws.on('message',data=>handleMessage(ws,data));ws.on('close',()=>{if(owner?.ws===ws)release();});});
 socket.on('message',raw=>{let m;try{m=validateRoverMessage(JSON.parse(String(raw)));}catch{return;}
  if(!['rover_state','rover_contact'].includes(m.type)||!owner||m.session_id!==owner.session||m.calibration_id!==lastState?.calibration_id)return;
  notify(owner.ws,m);
 });
 const ready=new Promise((resolve,reject)=>{socket.once('error',reject);socket.once('listening',resolve);});
 socket.on('error',e=>{if(!closing)console.error('Rover relay:',e.message);});socket.bind(roverStatePort,'127.0.0.1');
 return {handleMessage,ready,address:()=>socket.address(),close:()=>new Promise(resolve=>{closing=true;release();socket.close(resolve);})};
}
