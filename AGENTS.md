# AGENTS.md

Guidance for any coding agent (Claude Code, Codex, Cursor, Copilot) working in this repo.
**Talk to the user in Indonesian. Write code, identifiers and commit messages in English.**
Product requirements live in `PRD.md`: read it before changing behaviour.

## What this is

A personal job-radar portal for Indonesia: one static `index.html` that shows jobs on a 3D map (three.js: extruded
islands, instanced bars per city) with filters for industry, company, salary, posting time, location and validity. Data comes from a
`jobs.json` file (contract: `schema/jobs.schema.json`). Without it, the page shows clearly labelled **demo data**.

Status: Phase 0 (UI) done. Phase 1 partly done: `pipeline/` fetches Greenhouse, Lever, Workable and Workday JSON-LD for the
companies in `pipeline/companies.yaml`; GitHub Actions refreshes `jobs.json` every 3 hours. See PRD section 9.

## Layout

```
index.html              the whole portal: CSS, JS, and an embedded offline basemap (see "Land data")
schema/jobs.schema.json data contract between pipeline and portal
tools/build_land.mjs    regenerates the embedded basemap between <!--LAND:START--> and <!--LAND:END-->
tools/smoke.cjs         browser smoke test (Playwright); the definition of "works"
tools/fixtures/         saved real Wikipedia/Wikidata responses used by the smoke test (never hand-edit them)
PRD.md                  requirements, source strategy, validity rules, phases
```

`pipeline/` (Python 3.12, SQLite, PyYAML): one module per source in `pipeline/sources/`, same interface (see its
`__init__.py`), `run.py` exports `jobs.json`. Every request goes through `pipeline/http.py`, which honours robots.txt and
Crawl-delay and stops a board on HTTP 429. `.github/workflows/update-jobs.yml` runs tests + pipeline every 3 hours and
commits `jobs.json` when it changed; that push deploys through Workers Builds.

Adding a company: verify its board answers on the documented public endpoint, that robots.txt allows it, and that it
has Indonesian postings; then add it to `companies.yaml` with an industry from the PRD taxonomy. Adding a source type:
save a real response in `pipeline/tests/fixtures/` first (see its README), write the test, then the parser.

## Commands

```bash
npm install && npx playwright install chromium   # once
npm run serve        # http://localhost:8080  (python http.server; jobs.json next to index.html is auto-loaded)
npm run smoke        # must print SMOKE OK before you call anything done
npm run build:land   # only if the basemap needs regenerating
npm run deploy       # Cloudflare Workers static assets -> https://job-radar.buitenzorg.dev (needs `wrangler login`)

python -m venv .venv && .venv/Scripts/pip install -r requirements.txt -r requirements-dev.txt   # once (bin/ on Linux)
.venv/Scripts/python -m pytest -q pipeline/tests    # parser tests against saved real samples, no network
.venv/Scripts/python -u -m pipeline.run             # live fetch -> jobs.json (+ pipeline/jobs.sqlite)
python -I tools/build_gazetteer.py cities15000.zip admin1CodesASCII.txt   # only to regenerate the GeoNames towns
```

Deploy uploads only `dist/`, which `tools/build_site.mjs` fills from an allowlist (`index.html`, `robots.txt`, `_headers`,
`favicon.svg`, `og-image.png`, `jobs.json` if present). It also pre-renders the 40 newest jobs into `dist/index.html`
(replaced by the app on load), puts live counts in the meta description and writes `sitemap.xml`. Anything in `dist/` is
public and the site is indexable (owner's decision, 25 Nov 2026). Security headers live in `_headers`; the page CSP is in
`index.html` and also allows Cloudflare Web Analytics, which the `buitenzorg.dev` zone injects.
`node tools/og_image.cjs` regenerates the 1200x630 social preview from the real page and the current `jobs.json`.

Opening `index.html` via `file://` works too (falls back to demo data; use the "Muat jobs.json" button).

## Hard rules

1. **Never write scrapers for sites whose terms forbid automated access** (LinkedIn, Indeed, Jobstreet/SEEK and
   similar). Allowed paths are the Tier A sources in PRD section 5: company career pages (JSON-LD, `robots.txt`
   respected), public ATS APIs, Telegram via the official API with the user's own account, the user's own email
   alerts, manual input, and search-shortcut *links*. If a task seems to need a Tier C scraper, stop and tell the user.
2. **Never present fake data as real.** Demo data stays labelled ("Data contoh") with fictional companies and no
   working links. Do not invent salaries: unknown salary is `null`.
3. **Do not store personal data** about recruiters or applicants. No secrets in the repo (Telegram session files,
   IMAP passwords, API keys): use environment variables and `.gitignore`.
4. **Escape everything from `jobs.json`** (`esc()` before it touches `innerHTML`) and only allow `http(s)` URLs.
5. **"Terverifikasi" must be earned** by the trust rubric in PRD section 7. Do not shortcut the label.

## Conventions

- Keep `index.html` a **single file with no build step and no framework**. Budget: under 250 KB, first paint under 2 s.
  New dependencies need a strong reason; prefer a few lines of plain JS.
- Pin CDN versions exactly (currently `three@0.187.0`, loaded through the import map in `<head>`; the map that rewrites
  `three.core.js` to `three.core.min.js` must keep the same version). Keep `three` in `package.json` at the same version:
  the smoke test serves it from `node_modules`.
- The 3D map is a `<script type="module">` that attaches itself via `JobRadar.attachMap()`. The list and filters must keep
  working without it (CDN down, no WebGL). It renders on demand only; do not add an always-running loop (the pulse rings
  are the one throttled exception, about 25 fps, off under reduced motion). Bars use a small `onBeforeCompile` gradient on
  `MeshStandardMaterial`; shadows come from one directional light; ground glow and the selected-city beam are additive.
- "Bidang" (job function) is derived in the portal from the title (`ROLES`); "Industri" is the employer's industry.
- Company profiles: `companies` in `jobs.json` first, Wikipedia/Wikidata only after the user clicks. Never send anything to a
  third party without a click, and keep the attribution. The CSP in `<head>` lists every allowed origin; update it on purpose.
- Indonesian for all user-facing text, English for code. Money is rupiah per month, shown as "Rp 12–18 jt".
- Time is stored in UTC ISO 8601 and shown relative ("3 jam lalu"). Use the gazetteer (`CITIES`) for coordinates;
  add a city there rather than hard-coding coordinates in data.
- Map bars are rescaled every frame from the camera distance so they keep a constant on-screen size. Do not switch to fixed world heights.
- localStorage access is always wrapped in try/catch (it can throw or be empty in private windows).
- Respect `prefers-color-scheme` and `prefers-reduced-motion`. Keep everything usable down to 360 px width.

## Land data

The offline basemap (Natural Earth 1:50m via `world-atlas`, coordinates rounded to ~2 km) is embedded in
`<script id="land-data">`. It sits at the **top** of the file, before the main script, and is one very long line:
never open-and-reformat it, and edit it only through `npm run build:land`.

## Definition of done

1. `npm run smoke` prints `SMOKE OK`.
2. You looked at the page in a real browser at desktop (about 1280 px) and phone (about 390 px) widths, light and dark.
3. If you changed the data contract, `schema/jobs.schema.json`, the normaliser in `index.html`, and PRD section 6 all agree.
4. If you added a source: parser unit tests using saved real samples, and the source is in the right PRD tier.

## Not verified yet (be honest about these)

- three.js is tested from `node_modules` (unminified). The jsDelivr auto-minified `*.min.js` files were checked to exist
  and to import `./three.core.js`, but the page was not loaded against the live CDN in the smoke test.
- The Wikipedia/Wikidata lookup is tested against saved real responses, not the live API. Matching by name can pick the
  wrong article for ambiguous names; the UI says so.
- The Jobstreet and Indeed search-shortcut URL formats could not be checked automatically (bot protection, HTTP 403).
- Low-end phones: frame rate on a real device was not measured (only headless Chromium with SwiftShader).
- The update workflow has run locally only until its first scheduled run on GitHub; check the Actions tab.
- Workday sitemaps of large tenants are often capped (about 100 URLs), so their coverage is partial.
- `index.html` contains the GeoNames towns between `/*GAZ:START*/` and `/*GAZ:END*/`; regenerate, never hand-edit.
