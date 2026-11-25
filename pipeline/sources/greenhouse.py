"""Greenhouse Job Board API (public, no auth): https://developers.greenhouse.io/job-board.html
GET https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"""
from __future__ import annotations

from ..models import Company, RawJob, html_to_text, parse_dt

NAME = "greenhouse"
LABEL = "ATS perusahaan (Greenhouse)"


def feed(cfg: dict) -> str:
    return f"{NAME}:{cfg['board']}"


def url(cfg: dict) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{cfg['board']}/jobs?content=true"


def parse(data: dict, company: Company, cfg: dict) -> list[RawJob]:
    out = []
    for j in (data or {}).get("jobs", []):
        loc = ((j.get("location") or {}).get("name") or "")
        text = html_to_text(j.get("content") or "")
        out.append(RawJob(
            feed=feed(cfg), source=NAME, source_id=str(j.get("id")), company=company.name,
            title=(j.get("title") or "").strip(), url=j.get("absolute_url") or "",
            locations=[p.strip() for p in loc.split(";") if p.strip()],
            work_type="remote" if "remote" in loc.lower() else None,
            posted_at=parse_dt(j.get("first_published") or j.get("updated_at")),
            department=", ".join(d.get("name", "") for d in j.get("departments") or [] if d.get("name")),
            text=text))
    return out
