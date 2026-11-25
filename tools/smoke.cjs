// Browser smoke test: loads index.html, exercises filters, import and safety, fails loudly on any problem.
//   npm i && npx playwright install chromium && npm run smoke
// MapLibre is served from node_modules, and the online basemap is blocked, so the test needs no internet.
const { chromium } = require('playwright');
const path = require('path');
const assert = require('assert');
const ML = path.join(__dirname, '..', 'node_modules', 'maplibre-gl', 'dist') + path.sep;
const PAGE = 'file://' + path.join(__dirname, '..', 'index.html');

(async () => {
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  const problems = [];
  page.on('pageerror', (e) => problems.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') problems.push(m.text()); });
  await page.route('**/maplibre-gl.js', (r) => r.fulfill({ path: ML + 'maplibre-gl.js', contentType: 'text/javascript' }));
  await page.route('**/maplibre-gl.css', (r) => r.fulfill({ path: ML + 'maplibre-gl.css', contentType: 'text/css' }));
  await page.route('**/basemaps.cartocdn.com/**', (r) => r.abort());
  await page.goto(PAGE);
  await page.waitForFunction(() => window.__bars > 0, null, { timeout: 20000 });

  const n = () => page.evaluate(() => +document.getElementById('count').textContent.match(/\d+/)[0]);
  const total = await n();
  assert(total > 50, 'demo data should load');

  await page.fill('#salMin', '20');
  const withSal = await n(); assert(withSal < total, 'salary filter narrows results');
  await page.uncheck('#unkSal');
  assert((await page.$$eval('.job .tag.sal', (e) => e.map((x) => x.textContent))).every((t) => !t.includes('tidak tercantum')), 'unknown salary hidden');
  await page.fill('#salMin', ''); await page.check('#unkSal');

  await page.click('#indDD summary'); await page.click('#industries input >> nth=0');
  const ind = await page.evaluate(() => document.querySelector('#industries input:checked').dataset.ind);
  assert((await page.$$eval('.job', (e) => e.map((x) => x.textContent))).every((t) => t.includes(ind)), 'industry filter applies');
  await page.click('#clear');

  await page.selectOption('#since', '24');
  assert((await page.$$('.job:not(:has(.tag.fresh))')).length === 0, '24h filter keeps only fresh jobs');
  await page.selectOption('#since', '0');

  await page.click('.lbl >> nth=0');
  assert(await page.evaluate(() => JobRadar.state.city !== null), 'clicking a city label selects the city');
  await page.click('#clear');

  const bad = { generated_at: new Date().toISOString(), jobs: [
    { id: 'a', title: '<img src=x onerror=window.__xss=1>Eng', company: 'PT Uji', city: 'Bogor', posted_at: new Date().toISOString(), url: 'javascript:alert(1)' },
    { id: 'b', title: 'Kota palsu', company: 'PT Uji', city: 'Atlantis', posted_at: new Date().toISOString() },
    { id: 'a', title: 'duplikat', company: 'PT Uji', city: 'Bogor', posted_at: new Date().toISOString() },
    { title: 'tanpa id' } ] };
  require('fs').writeFileSync(path.join(__dirname, '.bad.json'), JSON.stringify(bad));
  await page.setInputFiles('#file', path.join(__dirname, '.bad.json'));
  await page.waitForFunction(() => !JobRadar.state.demo);
  const r = await page.evaluate(() => ({ jobs: JobRadar.state.jobs.length, xss: window.__xss === 1, href: document.querySelector('.job .acts a').getAttribute('aria-disabled') }));
  require('fs').unlinkSync(path.join(__dirname, '.bad.json'));
  assert.strictEqual(r.jobs, 1, 'invalid, duplicate and unknown-city rows are dropped');
  assert.strictEqual(r.xss, false, 'imported HTML must be escaped');
  assert.strictEqual(r.href, 'true', 'non-http(s) URLs must not become links');

  // phone width: no horizontal scroll
  const phone = await (await browser.newContext({ viewport: { width: 390, height: 844 } })).newPage();
  await phone.route('**/maplibre-gl.js', (r) => r.fulfill({ path: ML + 'maplibre-gl.js', contentType: 'text/javascript' }));
  await phone.route('**/maplibre-gl.css', (r) => r.fulfill({ path: ML + 'maplibre-gl.css', contentType: 'text/css' }));
  await phone.route('**/basemaps.cartocdn.com/**', (r) => r.abort());
  await phone.goto(PAGE);
  await phone.waitForFunction(() => window.__bars > 0, null, { timeout: 20000 });
  assert(!(await phone.evaluate(() => document.documentElement.scrollWidth > innerWidth)), 'no horizontal scroll at 390px');

  assert.deepStrictEqual(problems, [], 'no console errors or page errors');
  console.log('SMOKE OK');
  await browser.close();
})().catch((e) => { console.error('SMOKE FAILED:', e.message); process.exit(1); });
