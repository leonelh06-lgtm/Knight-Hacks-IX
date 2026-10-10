// predictor.mjs: no hardware, no dependencies. Runs in Node or the browser.
export class DodgePredictor {
  constructor({ decay = 0.85, prior = 0.2, stayDist = 0.5 } = {}) {
    this.decay = decay;
    this.stayDist = stayDist; // set to about half the avatar diameter
    this.w = { PLUS: prior, MINUS: prior, TOWARD: prior, AWAY: prior, STAY: prior };
    this.n = 0;
  }
  // p0 = player position at warning start, p1 = at impact,
  // aim = unit vector from boss to player at lock.
  // PLUS/MINUS = the two sides of the attack axis. Which one is "left" depends
  // on whether y points up or down in your coordinates, so just stay consistent.
  classify(p0, p1, aim) {
    const dx = p1.x - p0.x, dy = p1.y - p0.y;
    if (Math.hypot(dx, dy) < this.stayDist) return 'STAY';
    const along = dx * aim.x + dy * aim.y;
    const side = dx * -aim.y + dy * aim.x;
    if (Math.abs(side) >= Math.abs(along)) return side > 0 ? 'PLUS' : 'MINUS';
    return along > 0 ? 'AWAY' : 'TOWARD';
  }
  observe(p0, p1, aim) {
    const dir = this.classify(p0, p1, aim);
    for (const k in this.w) this.w[k] *= this.decay;
    this.w[dir] += 1;
    this.n += 1;
    return dir;
  }
  predict() {
    const total = Object.values(this.w).reduce((a, b) => a + b, 0);
    const [dir, wt] = Object.entries(this.w).sort((a, b) => b[1] - a[1])[0];
    return { dir, confidence: wt / total, n: this.n };
  }
}
