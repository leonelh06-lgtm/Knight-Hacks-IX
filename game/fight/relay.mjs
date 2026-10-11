// relay.mjs: UDP JSON from gesture_control -> WebSocket for the browser game.
// Run: npm install ws   then   node relay.mjs   (start gesture_control with --udp-port 5005)
import dgram from 'node:dgram';
import { WebSocketServer } from 'ws';

const UDP_PORT = Number(process.env.UDP_PORT ?? 5005);
const WS_PORT = Number(process.env.WS_PORT ?? 8765);
const wss = new WebSocketServer({ port: WS_PORT });
const udp = dgram.createSocket('udp4');
let closing = false, udpReady = false, wsReady = false;
function shutdown(code = 0) {
  if (closing) return;
  closing = true;
  process.exitCode = code;
  for (const client of wss.clients) client.terminate();
  wss.close();
  try { udp.close(); } catch (error) {
    if (error.code !== 'ERR_SOCKET_DGRAM_NOT_RUNNING') throw error;
  }
}
function failed(transport, port, error) {
  if (closing) return;
  if (error.code === 'EADDRINUSE') {
    console.error(`${transport} port ${port} is already in use. Stop the existing relay with Ctrl+C in its terminal, then retry. If another application owns the port, close it first.`);
  } else {
    console.error(`${transport} startup failed on port ${port}: ${error.code ?? 'ERROR'}: ${error.message}`);
  }
  shutdown(1);
}
function ready() {
  if (!closing && udpReady && wsReady) console.log(`relay: udp ${udp.address().port} -> ws://localhost:${wss.address().port}`);
}
wss.on('error', error => failed('WebSocket', WS_PORT, error));
wss.on('listening', () => { wsReady = true; ready(); });

udp.on('message', (buf) => {
  let p;
  try { p = JSON.parse(buf.toString('utf8')); } catch { return; }
  if (!Number.isFinite(p.vx) || !Number.isFinite(p.vy)) return;
  // Re-stamp: the sender's timestamp is Python monotonic time, not comparable to the browser's.
  const msg = JSON.stringify({ vx: p.vx, vy: p.vy, active: !!p.active,
    status: p.status ?? '', mode: p.mode ?? '', recvAt: Date.now() });
  for (const ws of wss.clients) if (ws.readyState === 1) ws.send(msg);
});
udp.on('error', error => failed('UDP', UDP_PORT, error));
udp.bind(UDP_PORT, '127.0.0.1', () => { udpReady = true; ready(); });

for (const signal of ['SIGINT','SIGTERM']) process.on(signal, () => shutdown());
