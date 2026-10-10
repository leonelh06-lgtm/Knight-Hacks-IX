// maze_view.mjs: drawing code only for the Level 1 hedge maze. Phase 1 is
// deliberately flat/simple (colored rectangles and circles); Phase 2 replaces
// drawMazeFlat with the full storybook-forest rendering, keeping the same
// call shape so debug.html's wiring doesn't need to change.

const COLORS = { floor: '#2a3b2d', wall: '#355c3a', post: '#355c3a', goal: '#ffd700' };

// Simple Phase-1 rendering: flat floor, flat wall rectangles, flat corner
// post circles, dashed goal ring. `centerX`/`centerZ` place the maze's local
// (0,0)-centered geometry into world space; X/Z/S are debug.html's existing
// world -> screen helpers.
export function drawMazeFlat(ctx, { state, centerX, centerZ, X, Z, S }) {
  const { geom } = state;
  ctx.fillStyle = COLORS.floor;
  const pad = 1;
  ctx.fillRect(
    X(centerX + geom.originX - pad), Z(centerZ + geom.originZ - pad),
    (geom.P * state.maze.cols + pad * 2) * S, (geom.P * state.maze.rows + pad * 2) * S,
  );
  ctx.fillStyle = COLORS.wall;
  for (const w of geom.walls) {
    ctx.fillRect(X(centerX + w.cx - w.hw), Z(centerZ + w.cz - w.hh), (w.hw * 2) * S, (w.hh * 2) * S);
  }
  ctx.fillStyle = COLORS.post;
  for (const p of geom.posts) {
    ctx.beginPath(); ctx.arc(X(centerX + p.x), Z(centerZ + p.z), p.r * S, 0, Math.PI * 2); ctx.fill();
  }
  ctx.save();
  ctx.setLineDash([10, 7]); ctx.lineWidth = 4; ctx.strokeStyle = COLORS.goal;
  ctx.shadowColor = COLORS.goal; ctx.shadowBlur = 12;
  ctx.beginPath(); ctx.arc(X(centerX + state.goal.x), Z(centerZ + state.goal.z), state.goalRadius * S, 0, Math.PI * 2); ctx.stroke();
  ctx.restore();
}

export function drawMazeHUD(ctx, state, extra) {
  const lines = [
    `${extra.levelName} | timer ${state.elapsed.toFixed(1)}s${state.paused ? ' (PAUSED - show your hand)' : ''}`,
    `speed ${extra.heroSpeed.toFixed(2)} | packets/s ${extra.pps} | mirrored ${state.maze.mirrored ? 'Y' : 'N'} (Y)`,
    `R restart | N skip level | H hide HUD`,
  ];
  const font = 20, pad = 10, w = 560, h = lines.length * (font + 6) + pad * 2;
  ctx.save();
  ctx.fillStyle = 'rgba(10,10,16,0.78)';
  ctx.fillRect(pad, 140, w, h);
  ctx.fillStyle = '#fff'; ctx.font = `${font}px monospace`;
  lines.forEach((line, i) => ctx.fillText(line, pad + 10, 140 + pad + font + i * (font + 6)));
  ctx.restore();
}

export function drawClearScreen(ctx, canvas, state) {
  ctx.save();
  ctx.fillStyle = 'rgba(0,0,0,0.45)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.textAlign = 'center';
  ctx.fillStyle = COLORS.goal; ctx.font = 'bold 40px monospace';
  ctx.fillText('LEVEL CLEAR', canvas.width / 2, canvas.height / 2 - 30);
  ctx.font = 'bold 28px monospace';
  ctx.fillText('★'.repeat(state.stars) + '☆'.repeat(3 - state.stars), canvas.width / 2, canvas.height / 2 + 10);
  ctx.font = '20px monospace'; ctx.fillStyle = '#fff';
  ctx.fillText(`${state.elapsed.toFixed(1)}s`, canvas.width / 2, canvas.height / 2 + 40);
  ctx.textAlign = 'left';
  ctx.restore();
}
