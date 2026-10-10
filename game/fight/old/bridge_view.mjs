// bridge_view.mjs: drawing code only for the Rope Bridge level. No physics, no
// input -- everything here reads a bridge.mjs state/config and draws it, plus
// the (u,v) -> world coordinate transform that VIEW_ROT controls (bridge.mjs
// never sees this; it only knows local u/v). debug.html calls uvToWorld() each
// frame to place the hero sprite (drawn by debug.html's own existing code, not
// duplicated here) and calls the draw* functions below for the bridge itself.

function rotateVec(vec, deg) {
  const rad = (deg * Math.PI) / 180;
  const c = Math.cos(rad), s = Math.sin(rad);
  return { x: vec.x * c - vec.z * s, z: vec.x * s + vec.z * c };
}
// VIEW_ROT=0: u runs along -z (the old top-down "forward"), v along +x.
// VIEW_ROT=90 (default): u runs along +x (a long bridge fits a wide screen), v along +z.
export function axesForViewRot(viewRot) {
  return { uAxis: rotateVec({ x: 0, z: -1 }, viewRot), vAxis: rotateVec({ x: 1, z: 0 }, viewRot) };
}
// LENGTH = the arena's dimension along the rendered u axis, minus 1.6 units margin.
export function lengthForViewRot(viewRot, room) {
  const { uAxis } = axesForViewRot(viewRot);
  const extent = Math.abs(uAxis.x) > 0.5 ? (room.maxX - room.minX) : (room.maxZ - room.minZ);
  return Math.max(1, extent - 1.6);
}
export function uvToWorld({ u, v }, viewRot, room) {
  const { uAxis, vAxis } = axesForViewRot(viewRot);
  const length = lengthForViewRot(viewRot, room);
  const cx = (room.minX + room.maxX) / 2, cz = (room.minZ + room.maxZ) / 2;
  const ox = cx - uAxis.x * (length / 2), oz = cz - uAxis.z * (length / 2);
  return { x: ox + uAxis.x * u + vAxis.x * v, z: oz + uAxis.z * u + vAxis.z * v };
}

function themeColors(theme) {
  // THEME 'bright': lit white board, use hue contrast not darkness. 'dark': near-black chasm.
  return theme === 'dark'
    ? { chasm: '#050912', bridge: '#3a3226', edge: '#9a8a66' }
    : { chasm: '#bfe9ff', bridge: '#cdb78a', edge: '#8a7340' };
}

// Minimal Phase 1 rendering: a rectangle bridge, a bright/dark chasm fill, and
// edge lines. Phase 2 replaces this with planks, mist, telegraphs, etc.
export function drawBridge(ctx, { state, viewRot, room, X, Z }) {
  const config = state.config;
  const colors = themeColors(config.THEME);
  const length = lengthForViewRot(viewRot, room);
  const hw = config.HALF_WIDTH;
  const corners = [[0, -hw], [length, -hw], [length, hw], [0, hw]].map(([u, v]) => uvToWorld({ u, v }, viewRot, room));

  ctx.fillStyle = colors.chasm;
  ctx.fillRect(X(room.minX), Z(room.minZ), X(room.maxX) - X(room.minX), Z(room.maxZ) - Z(room.minZ));

  ctx.beginPath();
  ctx.moveTo(X(corners[0].x), Z(corners[0].z));
  for (const c of corners.slice(1)) ctx.lineTo(X(c.x), Z(c.z));
  ctx.closePath();
  ctx.fillStyle = colors.bridge;
  ctx.fill();

  ctx.strokeStyle = colors.edge; ctx.lineWidth = 4;
  ctx.beginPath(); ctx.moveTo(X(corners[0].x), Z(corners[0].z)); ctx.lineTo(X(corners[1].x), Z(corners[1].z)); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(X(corners[3].x), Z(corners[3].z)); ctx.lineTo(X(corners[2].x), Z(corners[2].z)); ctx.stroke();
}

export function drawPauseOverlay(ctx, canvas) {
  ctx.save();
  ctx.fillStyle = 'rgba(0,0,0,0.5)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#ffd700'; ctx.font = 'bold 36px monospace'; ctx.textAlign = 'center';
  ctx.fillText('SHOW YOUR HAND', canvas.width / 2, canvas.height / 2);
  ctx.textAlign = 'left';
  ctx.restore();
}

// Larger-font HUD panel on a dark backing, toggled by key H (hidden by default).
export function drawHUD(ctx, state, viewRot, extra) {
  const c = state.config;
  const lines = [
    `Rope Bridge | seed ${state.seed} | VIEW_ROT ${viewRot} (K) | FORWARD_MODE ${state.forwardMode} (F)`,
    `phase ${state.phase}${state.paused ? ' | PAUSED' : ''} | u ${state.u.toFixed(2)}/${c.LENGTH.toFixed(2)} | v ${state.v.toFixed(2)} | HALF_WIDTH ${c.HALF_WIDTH.toFixed(2)} (9/0)`,
    `falls ${state.falls} | checkpoint ${state.checkpoint} | gustScale ${(c.gustScale ?? 1).toFixed(2)} (7/8)`,
    `require hand ${extra.requireHand ? 'ON' : 'OFF'} (Q) | R restart | N skip level | H hide HUD`,
  ];
  const font = 20, pad = 10, w = 620, h = lines.length * (font + 6) + pad * 2;
  ctx.save();
  ctx.fillStyle = 'rgba(10,10,16,0.78)';
  ctx.fillRect(pad, 140, w, h);
  ctx.fillStyle = '#fff'; ctx.font = `${font}px monospace`;
  lines.forEach((line, i) => ctx.fillText(line, pad + 10, 140 + pad + font + i * (font + 6)));
  ctx.restore();
}
