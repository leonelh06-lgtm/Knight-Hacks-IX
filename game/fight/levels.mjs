// Level progression. Level 2 is a 20-second contact-only survival hunt.
export const LEVELS = [
  {
    name: 'The Hedge Maze', map: 'maps/level1.png', mode: 'maze', heroSpeed: 2.4,
    laneAssist: 0.6, wallT: 0.32, starThresholds: { three: 40, two: 70 },
  },
  {
    // "use the existing map" for Phase 1; Phase 2 adds assets/l2_forest.png.
    name: 'The Corrupted Grove', map: 'maps/level2.png', mode: 'l2', heroSpeed: 3,
    l2: { SURVIVE_TIME: 20 },
  },
  {
    // level2.png now belongs to "The Corrupted Grove"; reusing level1.png here
    // is an imperfect placeholder (note: both maze.mjs and this boss level
    // now reference it), acceptable since re-skinning Ruins is out of scope
    // for this task.
    name: 'Ruins', map: 'maps/level1.png', mode: 'boss', bossMode: 'adaptive', warning: 1.5,
    heroSpeed: 3, pillars: true, start: { x: 0, z: 5 },
  },
  {
    name: 'Boss Arena', map: 'maps/boss.png', mode: 'boss', bossMode: 'adaptive', warning: 1.3,
    heroSpeed: 3, pillars: false, start: { x: 0, z: 5 },
  },
];
