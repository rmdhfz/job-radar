"""Fetch every board in companies.yaml, update the store, export jobs.json.

    python -m pipeline.run                       # writes jobs.json next to index.html
    python -m pipeline.run --out /tmp/jobs.json --db pipeline/jobs.sqlite
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from .http import Http
from .models import Company, iso, parse_dt
from .normalize import TAXONOMY, normalize
from .sources import SOURCES
from .store import Store

ROOT = Path(__file__).resolve().parent.parent
VOLATILE = ("generated_at", "last_verified_at", "fetched_at")


def load_companies(path: Path = ROOT / "pipeline" / "companies.yaml") -> list[Company]:
    rows = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    out = []
    for r in rows:
        if r.get("industry") not in TAXONOMY:
            raise ValueError(f"{r.get('name')}: industry must be one of the PRD taxonomy, got {r.get('industry')!r}")
        for s in r.get("sources") or []:
            if s.get("type") not in SOURCES:
                raise ValueError(f"{r['name']}: unknown source type {s.get('type')!r}")
        out.append(Company(name=r["name"], industry=r["industry"], website=r.get("website", ""), sources=r.get("sources") or []))
    return out


def collect(companies: list[Company], http, store: Store, now: datetime) -> list[dict]:
    report = []
    configured = set()
    for co in companies:
        for cfg in co.sources:
            mod = SOURCES[cfg["type"]]
            feed = mod.feed(cfg)
            configured.add(feed)
            try:
                raws = mod.fetch(cfg, co, http, store, now) if hasattr(mod, "fetch") else mod.parse(http.get_json(mod.url(cfg)), co, cfg)
            except Exception as e:  # one broken board must not stop the run, and must not expire its jobs
                store.log(now, feed, False, error=str(e)[:300])
                report.append({"feed": feed, "company": co.name, "ok": False, "error": str(e)[:200], "fetched_at": iso(now)})
                print(f"  FAIL {feed}: {e}", file=sys.stderr)
                continue
            jobs, skipped = [], Counter()
            for r in raws:
                j, why = normalize(r, co, mod.LABEL, now)
                if j:
                    jobs.append(j)
                else:
                    skipped[why] += 1
            store.record(feed, jobs, now)
            store.log(now, feed, True, len(raws), len(jobs), dict(skipped))
            report.append({"feed": feed, "company": co.name, "ok": True, "fetched": len(raws), "kept": len(jobs),
                           "skipped": dict(skipped), "fetched_at": iso(now)})
            print(f"  ok   {feed}: {len(raws)} fetched, {len(jobs)} in Indonesia kept, skipped {dict(skipped)}")
    store.retire(configured)
    return report


def dedupe(jobs: list[dict]) -> list[dict]:
    """PRD section 7: same company + title + city is one job; keep the most trusted copy."""
    best: dict[tuple, dict] = {}
    for j in jobs:
        k = (j["company"].lower(), " ".join(j["title"].lower().split()), j["city"])
        if k not in best or j["trust"] > best[k]["trust"]:
            best[k] = j
    return sorted(best.values(), key=lambda j: j["posted_at"], reverse=True)


def export(store: Store, companies: list[Company], report: list[dict], now: datetime) -> dict:
    return {
        "generated_at": iso(now),
        "jobs": dedupe(store.active()),
        "companies": {c.name: {k: v for k, v in {"website": c.website, "industry": c.industry, "source_label": "companies.yaml"}.items() if v}
                      for c in companies},
        "sources": report,
    }


def _stable(doc: dict) -> str:
    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if k not in VOLATILE}
        if isinstance(o, list):
            return [strip(v) for v in o]
        return o
    return json.dumps(strip(doc), sort_keys=True, ensure_ascii=False)


def write_if_changed(path: Path, doc: dict, now: datetime, refresh_hours: int = 20) -> bool:
    """Skip rewriting when only timestamps changed, unless the file is older than refresh_hours.
    Keeps the git history small (the workflow commits jobs.json) while timestamps never get older than a day."""
    if path.exists():
        try:
            old = json.loads(path.read_text(encoding="utf-8"))
            fresh = now - (parse_dt(old.get("generated_at")) or now - timedelta(days=99)) < timedelta(hours=refresh_hours)
            if fresh and _stable(old) == _stable(doc):
                return False
        except (ValueError, AttributeError):
            pass
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return True


def validate(doc: dict):
    try:
        import jsonschema
    except ImportError:
        return
    jsonschema.validate(doc, json.loads((ROOT / "schema" / "jobs.schema.json").read_text(encoding="utf-8")))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "jobs.json"))
    ap.add_argument("--db", default=str(ROOT / "pipeline" / "jobs.sqlite"))
    a = ap.parse_args(argv)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    companies = load_companies()
    store = Store(a.db)
    print(f"Fetching {sum(len(c.sources) for c in companies)} boards for {len(companies)} companies…")
    report = collect(companies, Http(), store, now)
    store.purge(now)
    doc = export(store, companies, report, now)
    validate(doc)
    changed = write_if_changed(Path(a.out), doc, now)
    ok = sum(r["ok"] for r in report)
    print(f"{len(doc['jobs'])} jobs exported, {ok}/{len(report)} boards ok, jobs.json {'written' if changed else 'unchanged'}")
    return 0 if ok else 1  # all boards failing is an error; a few failing is reported but not fatal


if __name__ == "__main__":
    sys.exit(main())
