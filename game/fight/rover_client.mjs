import {validateRoverMessage} from './rover_protocol.mjs';
export function createRoverClient({socket,sessionId,calibration,onContact=()=>false,onState=()=>{}}) {
 let claimed=false,closed=false,seq=0,lastState=null,telemetrySeq=-1;
 const send=m=>{if(socket.readyState===1){socket.send(JSON.stringify(m));return true;}return false;};
 const claim=()=>{if(!closed)send({type:'claim_game',version:1,session_id:sessionId});};
 function acknowledgeContact(event) {
  if(!claimed||closed||event.session_id!==sessionId||event.calibration_id!==calibration?.calibration_id)return false;
  return send({type:'contact_ack',version:1,session_id:sessionId,calibration_id:calibration.calibration_id,event_id:event.event_id});
 }
 const message=ev=>{
  let m;try{m=JSON.parse(ev.data);}catch{return;}
  if(m.type==='game_claimed'&&m.session_id===sessionId){claimed=true;return;}
  if(m.type==='game_claim_rejected'&&m.session_id===sessionId){claimed=false;onState({status:'Another tab owns the rover'});return;}
  if(!claimed||m.session_id!==sessionId||m.calibration_id!==calibration?.calibration_id)return;
  try{validateRoverMessage(m);}catch{return;}
  if(m.type==='rover_state'&&m.seq>telemetrySeq){telemetrySeq=m.seq;onState(m);}
  if(m.type==='rover_contact'&&lastState?.physical_boss&&lastState.level_id===m.level_id&&onContact(m))acknowledgeContact(m);
 };
 const disconnected=()=>{claimed=false;onState({armed:false,status:'Relay disconnected'});};
 socket.addEventListener('open',claim);socket.addEventListener('message',message);socket.addEventListener('close',disconnected);
 if(socket.readyState===1)claim();
 return {
  publishGame(state) {
   if(closed||!claimed||!calibration)return false;
   const m={...state,type:'game_state',version:1,session_id:sessionId,calibration_id:calibration.calibration_id,arena:calibration.arena,seq:seq++};
   validateRoverMessage(m);lastState=m;return send(m);
  },
  acknowledgeContact,
  close() {
   if(lastState&&claimed)send({...lastState,seq:seq++,active:false});
   closed=true;claimed=false;
   socket.removeEventListener('open',claim);socket.removeEventListener('message',message);socket.removeEventListener('close',disconnected);
  },
  get claimed(){return claimed;}
 };
}
