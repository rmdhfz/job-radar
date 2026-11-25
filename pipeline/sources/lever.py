"""Lever Postings API (public, no auth): https://github.com/lever/postings-api
GET https://api.lever.co/v0/postings/{site}?mode=json   (robots.txt: Crawl-delay 1, honoured by Http)"""
from __future__ import annotations

from ..models import Company, RawJob, parse_dt

NAME = "lever"
LABEL = "ATS perusahaan (Lever)"
WORK = {"onsite": "onsite", "on-site": "onsite", "hybrid": "hybrid", "remote": "remote"}


def feed(cfg: dict) -> str:
    return f"{NAME}:{cfg['site']}"


def url(cfg: dict) -> str:
    return f"https://api.lever.co/v0/postings/{cfg['site']}?mode=json"


def _salary(p: dict) -> tuple[float | None, float | None]:
    s = p.get("salaryRange") or {}
    if (s.get("currency") or "").upper() != "IDR" or s.get("interval") != "per-month-salary":
        return None, None  # only structured rupiah per month; anything else stays unknown
    lo, hi = s.get("min"), s.get("max")
    return (float(lo) if lo else None), (float(hi) if hi else None)


def parse(data: list, company: Company, cfg: dict) -> list[RawJob]:
    out = []
    for p in data or []:
        cat = p.get("categories") or {}
        locs = cat.get("allLocations") or ([cat["location"]] if cat.get("location") else [])
        lo, hi = _salary(p)
        out.append(RawJob(
            feed=feed(cfg), source=NAME, source_id=str(p.get("id")), company=company.name,
            title=(p.get("text") or "").strip(), url=p.get("hostedUrl") or p.get("applyUrl") or "",
            locations=list(locs), country=p.get("country"), work_type=WORK.get((p.get("workplaceType") or "").lower()),
            posted_at=parse_dt(p.get("createdAt")), department=cat.get("department") or cat.get("team") or "",
            employment_type=cat.get("commitment") or "", salary_min=lo, salary_max=hi,
            text=p.get("descriptionPlain") or p.get("openingPlain") or ""))
    return out
