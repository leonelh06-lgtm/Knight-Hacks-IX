// Canvas presentation for the 20-second hunt. All effects follow gameplay state.
export function drawHunters(ctx, state, { X, Z, S, t }) {
  ctx.save();
  for (const [i, h] of state.hunters.entries()) {
    const x = X(h.position.x), y = Z(h.position.z), r = h.radius * S;
    const warning = h.mode === 'warning', lunging = h.mode === 'lunge';
    const color = warning || lunging ? '#ff7945' : (i ? '#ffd052' : '#ffed8a');
    for (let j = 0; j < h.trail.length; j++) {
      const p = h.trail[j], alpha = (j + 1) / h.trail.length;
      ctx.globalAlpha = alpha * (lunging ? 0.38 : 0.13);
      ctx.fillStyle = color; ctx.beginPath(); ctx.arc(X(p.x), Z(p.z), r * alpha * 0.8, 0, Math.PI * 2); ctx.fill();
    }
    ctx.globalAlpha = 1;
    if (warning && state.phase === 'PLAYING') {
      // A short dashed path announces a body lunge, never a projectile.
      ctx.strokeStyle = '#ffbd72'; ctx.lineWidth = 2; ctx.setLineDash([6, 8]);
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + h.direction.x * S * 1.8, y + h.direction.z * S * 1.8); ctx.stroke(); ctx.setLineDash([]);
      ctx.strokeStyle = `rgba(255,130,80,${0.5 + 0.3 * Math.sin(t * 16)})`; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.arc(x, y, r + 8 + Math.sin(t * 16) * 3, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.shadowColor = color; ctx.shadowBlur = lunging ? 35 : 19;
    ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0; ctx.strokeStyle = '#fff6ca'; ctx.lineWidth = 2; ctx.stroke();
    ctx.save(); ctx.translate(x, y); ctx.rotate(Math.atan2(h.direction.z, h.direction.x));
    ctx.fillStyle = '#292018';
    for (const side of [-1, 1]) { ctx.beginPath(); ctx.ellipse(r * 0.35, side * r * 0.32, r * 0.22, r * 0.12, -side * 0.25, 0, Math.PI * 2); ctx.fill(); }
    ctx.restore();
    ctx.fillStyle = '#ffe6a9'; ctx.textAlign = 'center'; ctx.font = '600 10px sans-serif';
    ctx.fillText(warning ? 'LUNGE!' : h.name, x, y - r - 14);
  }
  ctx.restore();
}
export function drawHuntHUD(ctx, canvas, state, { t, calibrating = false }) {
  const { width: w, height: h } = canvas;
  ctx.save();
  // Keep the center readable; pressure gathers at the edges as hunters approach.
  const danger = state.phase === 'DEAD' ? 1 : state.danger;
  const pulse = 0.78 + Math.sin(t * (5 + danger * 7)) * 0.12;
  const shade = ctx.createRadialGradient(w / 2, h / 2, h * 0.22, w / 2, h / 2, Math.hypot(w, h) * 0.55);
  shade.addColorStop(0, 'rgba(6,15,16,0)');
  shade.addColorStop(1, `rgba(${danger > 0.55 ? '130,24,16' : '5,14,18'},${0.48 + danger * pulse * 0.35})`);
  ctx.fillStyle = shade; ctx.fillRect(0, 0, w, h);
  // Slow floating embers give the grove depth without obscuring enemy hit circles.
  for (let i = 0; i < 24; i++) {
    const px = (i * 173.7 + Math.sin(t * 0.4 + i) * 18 + w) % w;
    const py = ((i * 91.3 - t * (8 + i % 5)) % h + h) % h;
    ctx.fillStyle = `rgba(255,222,139,${0.1 + (Math.sin(t + i) + 1) * 0.1})`;
    ctx.beginPath(); ctx.arc(px, py, 1 + i % 2, 0, Math.PI * 2); ctx.fill();
  }
  const panelW = Math.min(440, w - 24), left = (w - panelW) / 2;
  ctx.fillStyle = 'rgba(8,17,19,0.86)'; ctx.fillRect(left, 18, panelW, 106);
  ctx.fillStyle = state.remaining <= 5 ? '#ff9270' : '#fbe5a1';
  ctx.fillRect(left, 18, panelW * state.remaining / state.duration, 3);
  ctx.textAlign = 'center'; ctx.font = '600 11px sans-serif';
  ctx.fillText('THE CORRUPTED GROVE  /  SURVIVE THE HUNT', w / 2, 42);
  ctx.font = '700 42px monospace'; ctx.fillText(state.remaining.toFixed(1), w / 2, 86);
  ctx.font = '12px sans-serif'; ctx.fillStyle = '#d8ded9';
  ctx.fillText(calibrating ? 'CALIBRATING — T TO RESUME' : 'TWO HUNTERS. ONE TOUCH. KEEP MOVING.', w / 2, 109);
  if (state.phase === 'PLAYING' && state.elapsed < 2.4 && !calibrating) {
    ctx.fillStyle = 'rgba(8,17,19,0.8)'; ctx.fillRect(w / 2 - 180, h - 88, 360, 54);
    ctx.fillStyle = '#fff0bd'; ctx.font = '600 18px sans-serif'; ctx.fillText('DON’T LET THEM TOUCH YOU', w / 2, h - 64);
    ctx.font = '12px sans-serif'; ctx.fillText('Survive 20 seconds · Move with your hand or WASD', w / 2, h - 44);
  } else if (state.phase === 'PLAYING' && state.remaining <= 5) {
    ctx.fillStyle = '#ffca96'; ctx.font = '700 18px sans-serif'; ctx.fillText('ALMOST THERE — KEEP MOVING', w / 2, h - 38);
  }
  if (state.phase === 'DEAD' || state.phase === 'CLEARED') {
    const dead = state.phase === 'DEAD';
    ctx.fillStyle = dead ? 'rgba(30,3,7,0.65)' : 'rgba(4,27,24,0.6)'; ctx.fillRect(0, 0, w, h);
    if (dead) {
      const age = Math.max(0, t - state.deadAt);
      ctx.strokeStyle = `rgba(255,129,84,${Math.max(0, 1 - age)})`; ctx.lineWidth = 5;
      ctx.beginPath(); ctx.arc(w / 2, h / 2, 40 + age * 200, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.fillStyle = dead ? '#ffb38f' : '#b9ffe0'; ctx.font = `800 ${Math.min(56, w / 10)}px sans-serif`;
    ctx.fillText(dead ? 'CAUGHT.' : 'YOU SURVIVED.', w / 2, h / 2 - 6);
    ctx.font = '16px sans-serif'; ctx.fillStyle = '#f2e8d9';
    ctx.fillText(dead ? 'Take a breath. The hunt restarts.' : 'The grove falls silent. Moving on…', w / 2, h / 2 + 32);
  }
  ctx.restore();
}
