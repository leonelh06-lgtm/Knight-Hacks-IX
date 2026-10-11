// Shared face overlay: draw in the sprite's local coordinates, after its image.
// The caller owns translation/rotation so the eyes follow Lenny in every scene.
export function drawLennyEyes(ctx, width, height, time = 0, waking = false) {
  const clamp = n => Math.max(0, Math.min(1, n));
  const wake = waking ? clamp((time - 2.7) / 0.8) : 1;
  const firstBlink = waking ? clamp(1 - Math.abs(time - 4.2) / 0.16) : 0;
  const cycle = ((time - 8) % 5.2 + 5.2) % 5.2;
  const blink = time >= 8 ? clamp(1 - Math.abs(cycle - 0.16) / 0.16) : 0;
  const openness = wake * (1 - Math.max(firstBlink, blink));
  ctx.save(); ctx.filter = 'none'; ctx.shadowBlur = 0;
  for (const side of [-1, 1]) {
    const x = side * width * 0.125, y = -height * 0.30;
    const rx = width * 0.012, ry = height * 0.023;
    ctx.strokeStyle = '#304132'; ctx.lineWidth = Math.max(0.4, width * 0.005);
    if (openness < 0.12) {
      ctx.beginPath(); ctx.moveTo(x - rx, y);
      ctx.quadraticCurveTo(x, y + ry * 0.36, x + rx, y); ctx.stroke();
      continue;
    }
    ctx.save(); ctx.translate(x, y); ctx.rotate(side * 0.28); ctx.scale(1, Math.max(0.12, openness));
    // The model's painted eyes: nearly black ovals, one small reflected highlight.
    ctx.fillStyle = '#15251f'; ctx.beginPath(); ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#263c31'; ctx.beginPath(); ctx.ellipse(-rx * 0.13, -ry * 0.1, rx * 0.72, ry * 0.78, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#101b17'; ctx.beginPath(); ctx.ellipse(rx * 0.08, ry * 0.16, rx * 0.72, ry * 0.73, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#97ac90'; ctx.beginPath(); ctx.ellipse(-rx * 0.26, -ry * 0.41, rx * 0.18, ry * 0.14, -0.25, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }
  ctx.restore();
}
