// levels.mjs: the fight's level progression. 'boss' levels pick the boss's aim
// strategy (see aim.mjs), how long the warning telegraph lasts before it fires
// (fed into fight.js's cfg.warning), and whether the pillar obstacles in
// debug.html are active. Level 1 is 'maze' (see maze.mjs): a fixed hedge-maze
// warm-up with no hazards, whose one true route is built to require all four
// gestures. heroSpeed/laneAssist/wallT/starThresholds are its tunables.
export const LEVELS = [
  {
    name: 'The Hedge Maze', map: 'maps/level1.png', mode: 'maze', heroSpeed: 2.4,
    laneAssist: 0.6, wallT: 0.32, starThresholds: { three: 40, two: 70 },
  },
  {
    name: 'Ruins', map: 'maps/level2.png', mode: 'boss', bossMode: 'adaptive', warning: 1.5,
    heroSpeed: 3, pillars: true, start: { x: 0, z: 5 },
  },
  {
    name: 'Boss Arena', map: 'maps/boss.png', mode: 'boss', bossMode: 'adaptive', warning: 1.3,
    heroSpeed: 3, pillars: false, start: { x: 0, z: 5 },
  },
];
