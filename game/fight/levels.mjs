// Level progression. Level 2 is a 20-second contact-only survival hunt.
export const LEVELS = [
  {
    id: 'hedge-maze', physicalBoss: false, name: 'The Hedge Maze', map: 'maps/level1.png', mode: 'maze', heroSpeed: 2.4,
    laneAssist: 0.6, wallT: 0.32, starThresholds: { three: 40, two: 70 },
  },
  {
    id: 'corrupted-grove', physicalBoss: false, name: 'The Corrupted Grove', map: 'maps/level2.png', mode: 'l2', heroSpeed: 3,
    l2: { SURVIVE_TIME: 20 },
  },
  {
    id: 'ruins', physicalBoss: false, name: 'Corrupted Sanctuary', map: 'maps/level3-corrupted.png', mode: 'boss', bossMode: 'adaptive', warning: 1.5,
    heroSpeed: 3, pillars: false, start: { x: 0, z: 5 },
  },
  {
    id: 'boss-arena', physicalBoss: true, name: 'Boss Arena', map: 'maps/boss.png', mode: 'boss', bossMode: 'adaptive', warning: 1.3,
    heroSpeed: 3, pillars: false, start: { x: 0, z: 5 },
  },
];
