"""Workable public jobs endpoint (no auth): https://workable.readme.io/reference/jobs-1
GET https://www.workable.com/api/accounts/{subdomain}?details=true   (302 -> apply.workable.com, both allowed by robots.txt)
Workable rate-limits quickly: one request per account per run."""
from __future__ import annotations

from ..models import Company, RawJob, html_to_text, parse_dt

NAME = "workable"
LABEL = "ATS perusahaan (Workable)"
WORK = {"on_site": "onsite", "onsite": "onsite", "hybrid": "hybrid", "remote": "remote"}


def feed(cfg: dict) -> str:
    return f"{NAME}:{cfg['account']}"


def url(cfg: dict) -> str:
    return f"https://www.workable.com/api/accounts/{cfg['account']}?details=true"


def parse(data: dict, company: Company, cfg: dict) -> list[RawJob]:
    out = []
    for j in (data or {}).get("jobs", []):
        parts = [j.get("city") or "", j.get("state") or "", j.get("country") or ""]
        loc = ", ".join(p for p in parts if p)
        locs = [loc] + [", ".join(x for x in (l.get("city"), l.get("region"), l.get("country")) if x) for l in j.get("locations") or [] if isinstance(l, dict)]
        wt = WORK.get((j.get("workplace_type") or "").lower()) or ("remote" if j.get("telecommuting") else None)
        codes = {(l.get("countryCode") or "").upper() for l in j.get("locations") or [] if isinstance(l, dict)}
        country = "ID" if (j.get("country") or "").strip().lower() == "indonesia" or "ID" in codes else None
        out.append(RawJob(
            feed=feed(cfg), source=NAME, source_id=str(j.get("shortcode") or j.get("code") or j.get("url")), company=company.name,
            title=(j.get("title") or "").strip(), url=j.get("url") or j.get("shortlink") or j.get("application_url") or "",
            locations=[l for l in locs if l], country=country, work_type=wt,
            posted_at=parse_dt(j.get("published_on") or j.get("created_at")), department=j.get("department") or "",
            employment_type=j.get("employment_type") or "", level=j.get("experience") or "",
            text=html_to_text(j.get("description") or "")))
    return out
