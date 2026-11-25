// Copies the files the portal serves into dist/, which is the only folder deployed to Cloudflare.
// An explicit allowlist: PRD, tools, schema, node_modules, pipeline data and secrets can never be uploaded by accident.
//   node tools/build_site.mjs   (wrangler runs it automatically before `wrangler deploy`, see wrangler.jsonc)
import fs from 'fs';
import path from 'path';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(\w:)/, '$1')), '..');
const OUT = path.join(ROOT, 'dist');
const FILES = ['index.html', 'robots.txt', '_headers'];
const OPTIONAL = ['jobs.json']; // pipeline output (Phase 1+); anything in dist/ is public

fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT);
for (const f of [...FILES, ...OPTIONAL]) {
  const src = path.join(ROOT, f);
  if (!fs.existsSync(src)) { if (FILES.includes(f)) throw new Error(`missing ${f}`); continue; }
  fs.copyFileSync(src, path.join(OUT, f));
}
const html = fs.readFileSync(path.join(OUT, 'index.html'), 'utf8');
if (!html.includes('<!--LAND:START-->')) throw new Error('index.html has no embedded basemap');
if (Buffer.byteLength(html) > 250 * 1024) throw new Error('index.html is over the 250 KB budget');
console.log('dist/:', fs.readdirSync(OUT).join(', '));
