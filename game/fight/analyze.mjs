// analyze.mjs: reads attack-log CSVs exported from debug.html (press L) and
// prints hit rate per mode and per player. One CSV file = one player's session.
// Run: node analyze.mjs <file1.csv> [file2.csv ...]
import fs from 'node:fs';

const files = process.argv.slice(2);
if (files.length === 0) {
  console.error('usage: node analyze.mjs <file1.csv> [file2.csv ...]');
  process.exit(1);
}

function parseCSV(text) {
  const lines = text.trim().split('\n');
  const header = lines[0].split(',');
  return lines.slice(1).filter(Boolean).map((line) => {
    const cells = line.split(',');
    const row = {};
    header.forEach((h, i) => (row[h] = cells[i]));
    row.hit = row.hit === 'true';
    return row;
  });
}

const pct = (hits, total) => (total ? (100 * hits / total).toFixed(0) : '0') + '%';
const bump = (map, key) => (map[key] ??= { hits: 0, total: 0 });

const byMode = {};
const byPlayer = {};
for (const file of files) {
  const rows = parseCSV(fs.readFileSync(file, 'utf8'));
  const player = bump(byPlayer, file);
  for (const row of rows) {
    const mode = bump(byMode, row.mode);
    mode.total += 1; player.total += 1;
    if (row.hit) { mode.hits += 1; player.hits += 1; }
  }
}

console.log('Per mode:');
for (const [mode, s] of Object.entries(byMode)) console.log(`  ${mode.padEnd(14)} ${s.hits}/${s.total}  ${pct(s.hits, s.total)}`);
console.log('Per player:');
for (const [player, s] of Object.entries(byPlayer)) console.log(`  ${player.padEnd(14)} ${s.hits}/${s.total}  ${pct(s.hits, s.total)}`);
