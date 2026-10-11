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
    id: 'ruins', physicalBoss: false, name: "T.K.'s Last Stand", map: 'maps/level3-corrupted.png', mode: 'tk',
    heroSpeed: 3, start: { x: 0, z: 5 }, bossPosition: { x: 0, z: 3.0 },
  },
];
