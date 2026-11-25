# AGENTS.md

Guidance for any coding agent (Claude Code, Codex, Cursor, Copilot) working in this repo.
**Talk to the user in Indonesian. Write code, identifiers and commit messages in English.**
Product requirements live in `PRD.md`: read it before changing behaviour.

## What this is

A personal job-radar portal for Indonesia: one static `index.html` that shows jobs on a 3D map (MapLibre GL, extruded
bars per city) with filters for industry, company, salary, posting time, location and validity. Data comes from a
`jobs.json` file (contract: `schema/jobs.schema.json`). Without it, the page shows clearly labelled **demo data**.

Status: Phase 0 (UI) done. Phase 1+ (ingestion pipeline) not started. See PRD section 9.

## Layout

```
index.html              the whole portal: CSS, JS, and an embedded offline basemap (see "Land data")
schema/jobs.schema.json data contract between pipeline and portal
tools/build_land.mjs    regenerates the embedded basemap between <!--LAND:START--> and <!--LAND:END-->
tools/smoke.cjs         browser smoke test (Playwright); the definition of "works"
PRD.md                  requirements, source strategy, validity rules, phases
```

Future (Phase 1+) goes in `pipeline/` (Python 3.12, SQLite): one module per source, same interface, exports `jobs.json`.

## Commands

```bash
npm install && npx playwright install chromium   # once
npm run serve        # http://localhost:8080  (python http.server; jobs.json next to index.html is auto-loaded)
npm run smoke        # must print SMOKE OK before you call anything done
npm run build:land   # only if the basemap needs regenerating
```

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
- Pin CDN versions exactly (currently `maplibre-gl@5.24.1`; v6 is ESM-only and breaks the plain `<script>` tag).
- Indonesian for all user-facing text, English for code. Money is rupiah per month, shown as "Rp 12–18 jt".
- Time is stored in UTC ISO 8601 and shown relative ("3 jam lalu"). Use the gazetteer (`CITIES`) for coordinates;
  add a city there rather than hard-coding coordinates in data.
- Map bars are rebuilt on zoom so they keep a constant on-screen size. Do not switch to fixed-meter heights.
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

- The optional online basemap ("Peta detail", CARTO style) was only tested for its failure path (fallback to the
  offline map), not against the live service.
- No real data source exists yet; every number on the page is demo data until Phase 1.
