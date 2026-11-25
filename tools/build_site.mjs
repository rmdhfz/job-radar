// Builds dist/, the only folder deployed to Cloudflare.
//  - An explicit allowlist: PRD, tools, schema, node_modules, pipeline data and secrets can never be uploaded by accident.
//  - SEO: pre-renders the newest jobs into index.html as plain HTML (replaced by the app on load), puts live counts in
//    the meta description, and writes sitemap.xml.
//   node tools/build_site.mjs   (wrangler runs it automatically before `wrangler deploy`, see wrangler.jsonc)
import fs from 'fs';
import path from 'path';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(\w:)/, '$1')), '..');
const OUT = path.join(ROOT, 'dist');
const SITE = 'https://job-radar.buitenzorg.dev/';
const FILES = ['index.html', 'robots.txt', '_headers', 'favicon.svg', 'og-image.png'];
const OPTIONAL = ['jobs.json']; // pipeline output; anything in dist/ is public

fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT);
for (const f of [...FILES, ...OPTIONAL]) {
  const src = path.join(ROOT, f);
  if (!fs.existsSync(src)) { if (FILES.includes(f)) throw new Error(`missing ${f}`); continue; }
  fs.copyFileSync(src, path.join(OUT, f));
}

const esc = (t) => String(t ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const httpUrl = (u) => { try { const x = new URL(u); return /^https?:$/.test(x.protocol) ? x.href : ''; } catch { return ''; } };
let html = fs.readFileSync(path.join(OUT, 'index.html'), 'utf8');
if (!html.includes('<!--LAND:START-->')) throw new Error('index.html has no embedded basemap');

let lastmod = new Date().toISOString();
const jobsPath = path.join(OUT, 'jobs.json');
if (fs.existsSync(jobsPath)) {
  const doc = JSON.parse(fs.readFileSync(jobsPath, 'utf8'));
  const jobs = (doc.jobs || []).filter((j) => j.status !== 'expired' && (j.trust ?? 50) >= 40);
  lastmod = doc.generated_at || lastmod;
  const companies = new Set(jobs.map((j) => j.company)).size, cities = new Set(jobs.map((j) => j.city)).size;
  const desc = `${jobs.length} lowongan kerja dari ${companies} perusahaan di ${cities} kota di Indonesia, di atas peta 3D. ` +
    'Diambil langsung dari situs karier dan ATS resmi perusahaan, dicek ulang tiap 3 jam.';
  html = html.replace(/<meta name="description" content="[^"]*">/, `<meta name="description" content="${esc(desc)}">`);
  const newest = [...jobs].sort((a, b) => String(b.posted_at).localeCompare(String(a.posted_at))).slice(0, 40);
  const cards = newest.map((j) => {
    const url = httpUrl(j.url);
    return `<article class="job" role="listitem"><div class="jtop"><h3>${url ? `<a class="open" href="${esc(url)}" rel="noopener noreferrer">${esc(j.title)}</a>` : esc(j.title)}</h3>` +
      `<span class="when">${esc(String(j.posted_at).slice(0, 10))}</span></div><div class="co"><span>${esc(j.company)} · ${esc(j.city)}${j.province ? ', ' + esc(j.province) : ''}</span></div></article>`;
  }).join('');
  const block = `<div id="list" role="list" tabindex="-1"><p class="sub" style="padding:4px 4px 10px">Lowongan terbaru (memuat peta dan filter…)</p>${cards}</div>`;
  if (!html.includes('<div id="list" role="list" tabindex="-1"></div>')) throw new Error('list placeholder not found');
  html = html.replace('<div id="list" role="list" tabindex="-1"></div>', block);
}
if (Buffer.byteLength(html) > 300 * 1024) throw new Error('dist/index.html is over 300 KB');
fs.writeFileSync(path.join(OUT, 'index.html'), html);
fs.writeFileSync(path.join(OUT, 'sitemap.xml'),
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
  `<url><loc>${SITE}</loc><lastmod>${lastmod.slice(0, 10)}</lastmod><changefreq>hourly</changefreq><priority>1.0</priority></url>\n</urlset>\n`);
console.log('dist/:', fs.readdirSync(OUT).join(', '), `| index.html ${Buffer.byteLength(html)} bytes`);
