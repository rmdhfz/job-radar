@AGENTS.md

# Claude Code notes

Read `PRD.md` first, then `AGENTS.md` (imported above). The rules in AGENTS.md "Hard rules" are not negotiable,
especially: **no scrapers for LinkedIn, Indeed or Jobstreet.**

## How to work here

- For anything bigger than a small fix (a new source, a schema change, a new UI feature), outline the change and the
  files you will touch before editing, and confirm against the relevant PRD section.
- Make small, reviewable commits. Do not reformat `index.html` or touch the `land-data` line.
- Verify UI changes in a browser, not just by reading code: run `npm run serve`, check desktop and phone widths in light
  and dark, then `npm run smoke`. Describe what you actually saw, not what you expect.
- When you add a source in Phase 1+, start from a **saved real sample** of its output, write the parser test against it,
  then the parser. Never fabricate sample jobs to make a test pass.
- If a source's terms or `robots.txt` are unclear, say so and ask the user; do not guess.
- Keep replies to the user short, in Indonesian, and say plainly what was and was not tested.

## Suggested first tasks (Phase 1, see PRD section 9)

1. `pipeline/` skeleton: `RawJob` model, `Source` interface, SQLite store, `export_jobs_json()` that conforms to the schema.
2. Greenhouse and Lever sources driven by a `companies.yaml` of 30 target companies (verify each endpoint in the official docs first).
3. JSON-LD `JobPosting` reader for company career pages, honouring `robots.txt`.
4. Search-shortcut links (F-9) in the portal for Tier C platforms.
