// tools/fake_gesture.mjs: fakes gesture_control's UDP output so the relay and
// debug.html can be tested without a camera.
// Run: node tools/fake_gesture.mjs   (then node relay.mjs, then serve debug.html)
import dgram from 'node:dgram';

const PORT = Number(process.env.UDP_PORT ?? 5005);
const sock = dgram.createSocket('udp4');

const cycle = [
  { vx: 0, vy: -1, status: 'open_palm', mode: 'cardinal' },    // up
  { vx: -1, vy: 0, status: 'pinch_index', mode: 'cardinal' },  // left
  { vx: 0, vy: 1, status: 'fist', mode: 'cardinal' },          // down
  { vx: 1, vy: 0, status: 'pinch_pinkie', mode: 'cardinal' },  // right
  { vx: 0, vy: 0, status: 'relaxed', mode: 'cardinal' },       // stop
];
let i = 0;
console.log(`fake_gesture: sending to 127.0.0.1:${PORT}, cycling up/left/down/right/stop every 1s`);
console.log('phase ->', cycle[i].status);
setInterval(() => {
  i = (i + 1) % cycle.length;
  console.log('phase ->', cycle[i].status);
}, 1000);
setInterval(() => {
  const c = cycle[i];
  const msg = JSON.stringify({ vx: c.vx, vy: c.vy, active: true, status: c.status, mode: c.mode, timestamp: Date.now() / 1000 });
  sock.send(msg, PORT, '127.0.0.1');
}, 50);
