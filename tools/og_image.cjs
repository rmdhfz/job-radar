// Renders og-image.png (1200x630, the social preview) from the real page and the current jobs.json.
//   node tools/og_image.cjs        (needs `npx playwright install chromium`; three.js is served from node_modules)
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const ROOT = path.join(__dirname, '..');

(async () => {
  if (!fs.existsSync(path.join(ROOT, 'jobs.json'))) throw new Error('jobs.json not found: run the pipeline first');
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await (await browser.newContext({ viewport: { width: 1200, height: 630 }, colorScheme: 'dark', deviceScaleFactor: 1 })).newPage();
  await page.route('**/cdn.jsdelivr.net/npm/three@*/**', (r) => {
    const rel = new URL(r.request().url()).pathname.replace(/^\/npm\/three@[^/]+\//, '').replace(/\.min\.js$/, '.js');
    r.fulfill({ path: path.join(ROOT, 'node_modules', 'three', rel), contentType: 'text/javascript' });
  });
  await page.goto('file://' + path.join(ROOT, 'index.html'));
  await page.waitForFunction(() => window.__bars > 0, null, { timeout: 30000 });
  await page.setInputFiles('#file', path.join(ROOT, 'jobs.json'));
  await page.waitForFunction(() => !JobRadar.state.demo);
  const n = await page.evaluate(() => ({ jobs: JobRadar.state.jobs.length, cos: new Set(JobRadar.state.jobs.map((j) => j.company)).size,
    cities: new Set(JobRadar.state.jobs.map((j) => j.city)).size }));
  await page.addStyleTag({ content: `.panel,.legend,.rank,.mapctl,.toast,.stats{display:none!important}.app{grid-template-columns:1fr!important}
    .og{position:absolute;left:56px;top:48px;z-index:9;color:#e8ecf2;font:700 54px/1.08 system-ui,"Segoe UI",sans-serif;letter-spacing:-.02em;text-shadow:0 2px 18px rgba(0,0,0,.6)}
    .og small{display:block;margin-top:14px;font:500 24px/1.35 system-ui,"Segoe UI",sans-serif;color:#b9c2d0;letter-spacing:0}
    .og i{font-style:normal;color:#8b83ff}` });
  await page.evaluate((n) => { const d = document.createElement('div'); d.className = 'og';
    d.innerHTML = `Radar Loker <i>Indonesia</i><small>${n.jobs} lowongan · ${n.cos} perusahaan · ${n.cities} kota<br>dari situs karier resmi, dicek tiap 3 jam</small>`;
    document.querySelector('.mapwrap').append(d); window.dispatchEvent(new Event('resize')); }, n);
  await page.waitForTimeout(800);
  await page.evaluate(() => JobRadar.map.home()); await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(ROOT, 'og-image.png') });
  await browser.close();
  console.log('og-image.png written', n);
})().catch((e) => { console.error(e.message); process.exit(1); });
