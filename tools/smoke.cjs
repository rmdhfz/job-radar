// Browser smoke test: loads index.html, exercises the 3D map, filters, detail dialog, company profile, import and safety.
// Fails loudly on any problem.   npm i && npx playwright install chromium && npm run smoke
// three.js is served from node_modules and Wikipedia/Wikidata from saved real responses (tools/fixtures), so no internet is needed.
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const assert = require('assert');
const THREE_DIR = path.join(__dirname, '..', 'node_modules', 'three');
const FIX = path.join(__dirname, 'fixtures');
const PAGE = 'file://' + path.join(__dirname, '..', 'index.html');
const json = (r, file) => r.fulfill({ path: path.join(FIX, file), contentType: 'application/json', headers: { 'access-control-allow-origin': '*' } });

async function wire(page, problems, wikiCalls) {
  page.on('pageerror', (e) => problems.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') problems.push(m.text()); });
  // jsDelivr serves auto-minified *.min.js; locally we serve the unminified twins from node_modules
  await page.route('**/cdn.jsdelivr.net/npm/three@*/**', (r) => {
    const rel = new URL(r.request().url()).pathname.replace(/^\/npm\/three@[^/]+\//, '').replace(/\.min\.js$/, '.js');
    r.fulfill({ path: path.join(THREE_DIR, rel), contentType: 'text/javascript' });
  });
  await page.route('**/*.wikipedia.org/**', (r) => {
    const u = new URL(r.request().url()); wikiCalls.push(u.href);
    const p = u.searchParams;
    if (p.get('generator') === 'search') return json(r, /telkom/i.test(p.get('gsrsearch')) ? 'wiki_search_telkom.json' : 'wiki_search_nomatch.json');
    if (p.get('prop') === 'extracts' && p.get('titles') === 'Telkom Indonesia') return json(r, 'wiki_full_telkom.json');
    return r.abort();
  });
  await page.route('**/www.wikidata.org/**', (r) => {
    const p = new URL(r.request().url()).searchParams; wikiCalls.push(r.request().url());
    if (p.get('ids') === 'Q2305438' && p.get('props') === 'claims') return json(r, 'wikidata_claims_Q2305438.json');
    if (p.get('props') === 'labels') return json(r, 'wikidata_labels_Q2305438.json');
    return r.abort();
  });
}

(async () => {
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  const problems = [], wikiCalls = [];
  await wire(page, problems, wikiCalls);
  await page.goto(PAGE);
  await page.waitForFunction(() => window.__bars > 0, null, { timeout: 30000 });
  assert(await page.evaluate(() => !!document.querySelector('#scene canvas')), 'three.js canvas exists');
  assert(await page.evaluate(() => document.getElementById('mapMsg').hidden), 'loading message hidden once the map is attached');

  const n = () => page.evaluate(() => +document.getElementById('count').textContent.match(/\d+/)[0]);
  const total = await n();
  assert(total > 50, 'demo data should load');
  assert(await page.evaluate(() => JobRadar.state.jobs.every((j) => j.company.startsWith('PT Demo'))), 'demo companies are fictional');

  // the full filter panel starts closed so the list gets the space; quick chips work without it
  assert(await page.evaluate(() => document.getElementById('filters').hidden), 'filter panel starts closed');
  await page.click('[data-quick="since:24"]');
  assert((await page.$$('.job:not(:has(.tag.fresh))')).length === 0, '24 jam chip keeps only fresh jobs');
  assert.strictEqual(await page.getAttribute('[data-quick="since:24"]', 'aria-pressed'), 'true', 'chip shows pressed state');
  assert.strictEqual(await page.textContent('#fcount'), '1', 'filter button counts active filters');
  await page.click('[data-quick="since:24"]');
  assert.strictEqual(await n(), total, 'pressing the chip again removes the filter');
  await page.click('[data-quick="sal"]');
  assert((await page.$$eval('.job .tag.sal', (e) => e.map((x) => x.textContent))).every((t) => !t.includes('tidak tercantum')), '"Ada gaji" chip hides unknown salaries');
  await page.click('[data-quick="sal"]');
  await page.click('[data-quick="role:IT & Software"]');
  const roles = await page.$$eval('.job', (e) => e.map((x) => x.textContent));
  assert(roles.length > 0 && roles.every((t) => t.includes('IT & Software')), '"IT & Software" chip keeps only IT roles');
  assert(await page.evaluate(() => JobRadar.state.jobs.filter((j) => /Backend Engineer|DevOps Engineer|IT Manager/.test(j.title)).every((j) => j.role === 'IT & Software')), 'IT titles are classified as IT');
  await page.click('[data-quick="role:IT & Software"]');
  await page.click('#fbtn');
  assert(await page.isVisible('#salMin'), 'Filter button opens the full panel');

  // suspect jobs (trust < 40) are hidden by default, PRD section 7
  await page.check('#susShow');
  assert((await n()) > total, 'showing suspect jobs adds rows');
  await page.uncheck('#susShow');

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
  await page.click('#fbtn');
  assert(!(await page.isVisible('#salMin')), 'Filter button closes the panel again');

  // map labels and the "Kota terpadat" ranking both select a city
  await page.click('.lbl >> nth=0');
  const city = await page.evaluate(() => JobRadar.state.city);
  assert(city !== null, 'clicking a city label selects the city');
  assert((await page.$$eval('.job .co', (e) => e.map((x) => x.textContent))).every((t) => t.includes(city)), 'list shows only the selected city');
  await page.click('#clear');
  await page.click('#rankList button >> nth=0');
  assert(await page.evaluate(() => JobRadar.state.city !== null), 'ranking button selects a city');
  await page.click('#clear');

  // clicking a bar in the 3D scene selects its city (raycast through the instanced mesh)
  // (use an isolated city: around Jakarta the bars overlap at the default zoom; wait for the camera flight to finish)
  await page.click('#reset'); await page.waitForTimeout(1300);
  const barHit = await page.evaluate(() => { const el = ['Makassar', 'Medan', 'Balikpapan', 'Batam'].map((c) => document.querySelector(`.lbl[data-city="${c}"]`)).find((e) => e && e.style.visibility !== 'hidden'); const r = el.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.bottom + 14, city: el.dataset.city }; });
  await page.mouse.click(barHit.x, barHit.y);
  assert.strictEqual(await page.evaluate(() => JobRadar.state.city), barHit.city, 'clicking a 3D bar selects that city');
  await page.click('#clear');

  // detail dialog: job tab, then company tab (demo: fictional profile, no external lookup)
  await page.click('.job .open >> nth=0');
  await page.waitForSelector('#detail[open]');
  const title = await page.textContent('.job .open >> nth=0');
  assert.strictEqual(await page.textContent('#dTitle'), title, 'detail shows the clicked job');
  assert(await page.isVisible('#pJob .trust'), 'detail shows the trust block');
  assert(await page.evaluate(() => location.hash.startsWith('#job=')), 'detail is deep-linkable');
  await page.click('#tabCo');
  assert(await page.isVisible('#pCo .co-head'), 'company tab renders');
  assert((await page.textContent('#pCo')).includes('fiktif'), 'demo company profile is labelled fictional');
  assert(!(await page.$('#pCo [data-wiki]')), 'no Wikipedia lookup for fictional companies');
  await page.keyboard.press('Escape');
  assert(!(await page.evaluate(() => document.getElementById('detail').open)), 'Escape closes the dialog');

  // import: invalid rows dropped, HTML escaped, non-http(s) links refused, company profiles sanitised
  const now = new Date().toISOString();
  const bad = { generated_at: now, jobs: [
    { id: 'a', title: '<img src=x onerror=window.__xss=1>Eng', company: 'PT Uji', city: 'Bogor', posted_at: now, url: 'javascript:alert(1)', trust: 80, status: 'active', summary: '<script>window.__xss=1</script>' },
    { id: 'b', title: 'Kota palsu', company: 'PT Uji', city: 'Atlantis', posted_at: now },
    { id: 'a', title: 'duplikat', company: 'PT Uji', city: 'Bogor', posted_at: now },
    { title: 'tanpa id' },
    { id: 'c', title: 'Network Engineer', company: 'PT Telkom Indonesia (Persero) Tbk', city: 'Bandung', posted_at: now, trust: 85, status: 'active', url: 'https://example.com/lowongan/1' },
    { id: 'd', title: 'Data Analyst', company: 'PT Sinar Kencana Datamas', city: 'Jakarta', posted_at: now, trust: 60 } ],
    companies: { 'PT Uji': { summary: '<img src=x onerror=window.__xss=1>', website: 'javascript:alert(1)', founded: 1999, source_label: 'Uji' } } };
  fs.writeFileSync(path.join(__dirname, '.bad.json'), JSON.stringify(bad));
  await page.setInputFiles('#file', path.join(__dirname, '.bad.json'));
  await page.waitForFunction(() => !JobRadar.state.demo);
  fs.unlinkSync(path.join(__dirname, '.bad.json'));
  const r = await page.evaluate(() => ({ jobs: JobRadar.state.jobs.length, xss: window.__xss === 1,
    href: document.querySelector('.job[data-id="a"] .acts a').getAttribute('aria-disabled') }));
  assert.strictEqual(r.jobs, 3, 'invalid, duplicate and unknown-city rows are dropped');
  assert.strictEqual(r.xss, false, 'imported HTML must be escaped');
  assert.strictEqual(r.href, 'true', 'non-http(s) URLs must not become links');

  await page.evaluate(() => JobRadar.openDetail('a', 'co'));
  await page.waitForSelector('#detail[open]');
  assert(await page.evaluate(() => window.__xss !== 1 && !document.querySelector('#detail img, #detail script')), 'detail and profile escape imported HTML');
  assert(await page.evaluate(() => [...document.querySelectorAll('#detail a')].every((a) => /^https?:|^#$/.test(a.getAttribute('href')))), 'detail only links http(s)');
  assert((await page.textContent('#pCo')).includes('1999'), 'company profile from jobs.json is shown');
  await page.keyboard.press('Escape');

  // Wikipedia profile from saved real responses: match, facts, history, attribution
  await page.evaluate(() => { try { localStorage.removeItem('jobradar.wiki'); } catch (e) {} JobRadar.openDetail('c', 'co'); });
  assert.strictEqual(wikiCalls.length, 0, 'nothing is sent to Wikipedia before the user clicks');
  await page.click('#pCo [data-wiki]');
  await page.waitForFunction(() => document.querySelector('#wiki .src'), null, { timeout: 10000 });
  const wiki = await page.textContent('#wiki');
  for (const want of ['Telkom Indonesia', 'Bandung', '1884', 'Sejarah', 'CC BY-SA']) assert(wiki.includes(want), `Wikipedia profile shows "${want}"`);
  assert(await page.$('#coLinks a[href^="https://www.telkom.co.id"]'), 'official site from Wikidata is linked');
  await page.keyboard.press('Escape');
  await page.evaluate(() => JobRadar.openDetail('d', 'co'));
  await page.click('#pCo [data-wiki]');
  await page.waitForFunction(() => /Tidak ada artikel/.test(document.getElementById('wiki').textContent), null, { timeout: 10000 });
  await page.keyboard.press('Escape');
  // unit checks on the matcher
  const m = await page.evaluate(() => ({
    generic: JobRadar.pickWikiPage({ query: { pages: [{ index: 1, title: 'Indonesia', pageprops: { wikibase_item: 'Q252' } }] } }, 'PT Telkom Indonesia Tbk'),
    univ: JobRadar.pickWikiPage({ query: { pages: [{ index: 1, title: 'Universitas Telkom', pageprops: { wikibase_item: 'Q1' } }, { index: 2, title: 'Telkom Indonesia', pageprops: { wikibase_item: 'Q2' } }] } }, 'PT Telkom Indonesia (Persero) Tbk'),
  }));
  assert.strictEqual(m.generic, null, 'a generic article title ("Indonesia") never matches');
  assert.strictEqual(m.univ && m.univ.title, 'Telkom Indonesia', 'exact name match beats a partial one');

  // phone width: no horizontal scroll, with and without the dialog
  const phone = await (await browser.newContext({ viewport: { width: 390, height: 844 }, colorScheme: 'dark' })).newPage();
  await wire(phone, problems, []);
  await phone.goto(PAGE);
  await phone.waitForFunction(() => window.__bars > 0, null, { timeout: 30000 });
  assert(!(await phone.evaluate(() => document.documentElement.scrollWidth > innerWidth)), 'no horizontal scroll at 390px');
  await phone.click('.job .open >> nth=0');
  await phone.waitForSelector('#detail[open]');
  assert(!(await phone.evaluate(() => document.querySelector('#detail .dbody').scrollWidth > document.querySelector('#detail .dbody').clientWidth + 1)), 'dialog has no horizontal scroll at 390px');

  assert.deepStrictEqual(problems, [], 'no console errors or page errors');
  console.log('SMOKE OK');
  await browser.close();
})().catch((e) => { console.error('SMOKE FAILED:', e.message); process.exit(1); });
