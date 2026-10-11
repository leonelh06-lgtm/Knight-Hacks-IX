// relay.mjs: UDP JSON from gesture_control -> WebSocket for the browser game.
// Run: npm install ws   then   node relay.mjs   (start gesture_control with --udp-port 5005)
import dgram from 'node:dgram';
import { WebSocketServer } from 'ws';

const UDP_PORT = Number(process.env.UDP_PORT ?? 5005);
const WS_PORT = Number(process.env.WS_PORT ?? 8765);
const wss = new WebSocketServer({ port: WS_PORT });
const udp = dgram.createSocket('udp4');

udp.on('message', (buf) => {
  let p;
  try { p = JSON.parse(buf.toString('utf8')); } catch { return; }
  if (!Number.isFinite(p.vx) || !Number.isFinite(p.vy)) return;
  // Re-stamp: the sender's timestamp is Python monotonic time, not comparable to the browser's.
  const msg = JSON.stringify({ vx: p.vx, vy: p.vy, active: !!p.active,
    status: p.status ?? '', mode: p.mode ?? '', recvAt: Date.now() });
  for (const ws of wss.clients) if (ws.readyState === 1) ws.send(msg);
});
udp.on('error', (e) => { console.error('UDP error:', e.message); process.exit(1); });
udp.bind(UDP_PORT, '127.0.0.1', () => console.log(`relay: udp ${UDP_PORT} -> ws://localhost:${WS_PORT}`));

for (const signal of ['SIGINT','SIGTERM']) process.on(signal, () => { udp.close(); wss.close(); });
