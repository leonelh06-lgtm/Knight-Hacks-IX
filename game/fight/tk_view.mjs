// Projected canvas presentation for TK's thirty-second survival battle.
export function drawTKArena(ctx, canvas, state, t) {
  const { width: w, height: h } = canvas;
  ctx.save();
  ctx.fillStyle = 'rgba(9,3,24,0.30)'; ctx.fillRect(0, 0, w, h);
  const edge = ctx.createRadialGradient(w / 2, h / 2, h * 0.12, w / 2, h / 2, Math.hypot(w, h) * 0.58);
  edge.addColorStop(0, 'rgba(4,2,14,0)');
  edge.addColorStop(1, state.phase === 'laser' ? 'rgba(93,4,20,0.78)' : 'rgba(7,2,29,0.74)');
  ctx.fillStyle = edge; ctx.fillRect(0, 0, w, h);
  for (let i = 0; i < 32; i++) {
    const x = (i * 173.7 + Math.sin(t * .5 + i) * 24 + w) % w;
    const y = ((i * 83.9 - t * (10 + i % 5)) % h + h) % h;
    ctx.globalAlpha = .11 + .15 * (1 + Math.sin(t * 2 + i)) / 2;
    ctx.fillStyle = i % 4 ? '#8cf9ff' : '#ff6a89';
    ctx.beginPath(); ctx.arc(x, y, 1 + i % 3, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}

export function drawTKBoss(ctx, state, { X, Z, S, t, sprite }) {
  const x = X(state.position.x), y = Z(state.position.z), r = 0.57 * S;
  ctx.save();
  // Runes and a moving energy halo give the boss a clear position beneath the tall sprite.
  ctx.translate(x, y);
  ctx.shadowColor = '#52e9ff'; ctx.shadowBlur = 28;
  ctx.strokeStyle = 'rgba(118,245,255,.86)'; ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.arc(0, 0, r + Math.sin(t * 3) * 3, 0, Math.PI * 2); ctx.stroke();
  ctx.shadowBlur = 0;
  ctx.rotate(t * 0.22);
  ctx.strokeStyle = 'rgba(151,119,255,.52)'; ctx.lineWidth = 2;
  for (let i = 0; i < 4; i++) {
    const a = i * Math.PI / 2;
    ctx.beginPath(); ctx.arc(0, 0, r + 12, a, a + .37); ctx.stroke();
  }
  ctx.restore();

  if (state.phase === 'warning' || state.phase === 'laser') {
    const a = Math.atan2(state.aim.z, state.aim.x), range = state.range * S;
    const charge = Math.max(0, Math.min(1, state.phaseElapsed));
    ctx.save();
    ctx.shadowColor = '#ff153e'; ctx.shadowBlur = state.phase === 'laser' ? 42 : 26;
    ctx.fillStyle = state.phase === 'laser' ? 'rgba(255,20,48,.68)' : `rgba(236,20,53,${.17 + charge * .25 + .06 * Math.sin(t * 22)})`;
    ctx.beginPath(); ctx.moveTo(x, y); ctx.arc(x, y, range, a - state.halfAngle, a + state.halfAngle); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = state.phase === 'laser' ? '#ff6b84' : '#ff335d';
    ctx.lineWidth = state.phase === 'laser' ? 5 : 2 + charge * 2;
    for (const side of [-1, 1]) {
      const edge = a + side * state.halfAngle;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(edge) * range, y + Math.sin(edge) * range); ctx.stroke();
    }
    ctx.restore();
    if (state.phase === 'laser') {
      const reach = Math.min(1, Math.max(.07, state.phaseElapsed / .20)) * range;
      const endX = x + state.aim.x * reach, endY = y + state.aim.z * reach;
      ctx.save(); ctx.lineCap = 'round'; ctx.shadowColor = '#ff0036'; ctx.shadowBlur = 38;
      ctx.strokeStyle = 'rgba(255,17,51,.7)'; ctx.lineWidth = 34;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(endX, endY); ctx.stroke();
      ctx.strokeStyle = '#ff5978'; ctx.lineWidth = 15; ctx.stroke();
      ctx.strokeStyle = '#fff2f2'; ctx.lineWidth = 5; ctx.stroke(); ctx.restore();
    }
  }
  ctx.save(); ctx.translate(x, y);
  const bob = Math.sin(t * 3.5) * 3;
  if (sprite?.complete && sprite.naturalWidth > 0) {
    const height = Math.max(112, Math.min(185, S * 2.3));
    const width = height * sprite.naturalWidth / sprite.naturalHeight;
    ctx.shadowColor = state.phase === 'warning' ? '#ff365d' : '#5cefff'; ctx.shadowBlur = 24;
    ctx.drawImage(sprite, -width / 2, -height * .86 + bob, width, height);
  } else {
    ctx.fillStyle = '#dde8fa'; ctx.shadowColor = '#5cefff'; ctx.shadowBlur = 20;
    ctx.beginPath(); ctx.arc(0, -r * .55, r * .7, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}

export function drawTKHUD(ctx, canvas, state, t) {
  const { width: w, height: h } = canvas;
  ctx.save();
  if (t < state.flashUntil) {
    ctx.fillStyle = `rgba(255,18,45,${.25 * Math.max(0, (state.flashUntil - t) / .35)})`;
    ctx.fillRect(0, 0, w, h);
  }
  const panelW = Math.min(490, w - 24), left = (w - panelW) / 2;
  ctx.fillStyle = 'rgba(8,5,27,.88)'; ctx.fillRect(left, 14, panelW, 112);
  ctx.fillStyle = state.remaining <= 5 ? '#ff456c' : '#69e8f8';
  ctx.fillRect(left, 14, panelW * state.remaining / state.duration, 4);
  ctx.textAlign = 'center'; ctx.font = '700 11px sans-serif'; ctx.fillStyle = '#b6e8f0';
  ctx.fillText("T.K.'S LAST STAND  /  SURVIVE 30 SECONDS", w / 2, 40);
  ctx.font = '800 43px monospace'; ctx.fillStyle = '#fff7ed';
  ctx.fillText(state.remaining.toFixed(1), w / 2, 85);
  ctx.font = '700 15px sans-serif';
  for (let i = 0; i < 3; i++) {
    ctx.fillStyle = i < state.health ? '#ff5576' : '#5c5665';
    ctx.fillText('◆', w / 2 + (i - 1) * 26, 111);
  }
  if (state.phase === 'warning' || state.phase === 'laser' || state.message === 'DODGED!' || state.message === 'LASER HIT!') {
    ctx.fillStyle = state.message === 'DODGED!' ? '#85ffe4' : '#ffb2c0';
    ctx.shadowColor = state.message === 'DODGED!' ? '#40ffd0' : '#ff3357'; ctx.shadowBlur = 16;
    ctx.font = `900 ${Math.min(40, w / 18)}px sans-serif`;
    ctx.fillText(state.message, w / 2, h - 47);
    ctx.shadowBlur = 0;
    if (state.phase === 'warning' && state.message === 'BOSS AWAKENED') {
      ctx.font = '600 14px sans-serif'; ctx.fillStyle = '#fff1ee';
      ctx.fillText('The red cone locks on. Move before the laser fires.', w / 2, h - 20);
    }
  }
  if (state.phase === 'victory' || state.phase === 'defeat') {
    ctx.fillStyle = state.phase === 'victory' ? 'rgba(1,22,27,.76)' : 'rgba(25,1,15,.79)';
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = state.phase === 'victory' ? '#a4fff1' : '#ff9ab0';
    ctx.font = `900 ${Math.min(64, w / 11)}px sans-serif`;
    ctx.fillText(state.phase === 'victory' ? 'YOU SURVIVED.' : 'LENNY FALLS.', w / 2, h / 2);
    ctx.font = '17px sans-serif'; ctx.fillStyle = '#fff6f1';
    ctx.fillText(state.phase === 'victory' ? 'T.K. lowers his weapon. The forest is yours.' : 'Three strikes. The battle begins again…', w / 2, h / 2 + 39);
  }
  ctx.restore();
}
