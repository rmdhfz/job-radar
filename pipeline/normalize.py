"""RawJob -> one job row of the jobs.json contract (schema/jobs.schema.json)."""
from __future__ import annotations

import hashlib
from datetime import datetime

from . import geo
from .models import Company, RawJob, iso, summarize
from .score import trust

TAXONOMY = {"Teknologi Informasi", "Perbankan & Keuangan", "Pertambangan", "Energi", "Manufaktur & FMCG", "Retail & E-commerce",
            "Logistik & Pelayaran", "Telekomunikasi", "Kesehatan", "Pendidikan", "Pemerintahan & BUMN", "Lainnya"}


def job_id(raw: RawJob) -> str:
    return f"{raw.source}-" + hashlib.sha1(f"{raw.feed}|{raw.source_id}".encode()).hexdigest()[:12]


def normalize(raw: RawJob, company: Company, label: str, now: datetime) -> tuple[dict | None, str]:
    """Returns (job, "") or (None, reason) where reason is "outside-id", "unknown-city" or "invalid"."""
    if not raw.title or not raw.url.startswith(("https://", "http://")):
        return None, "invalid"
    place = geo.resolve(raw.locations, raw.country, raw.title)
    if not place.indonesia:
        return None, "outside-id"
    work = raw.work_type or ("remote" if place.remote else None)
    if place.city is None and work != "remote":
        return None, "unknown-city"
    city = place.city or "Remote"
    posted = raw.posted_at or now  # unknown date: first seen (flagged in source_label)
    score, _ = trust(official=True, verified_now=True, complete=bool(raw.title and company.name and place.city),
                     url=raw.url, website=company.website, text=raw.text)
    job = {
        "id": job_id(raw), "title": raw.title[:160], "company": company.name,
        "industry": company.industry if company.industry in TAXONOMY else "Lainnya",
        "city": city, "work_type": work or "onsite",
        "salary_min": raw.salary_min, "salary_max": raw.salary_max,
        "posted_at": iso(posted), "last_verified_at": iso(raw.checked_at or now), "status": "active", "trust": score,
        "source_label": label + ("" if raw.posted_at else " · tanggal = pertama terlihat"), "url": raw.url,
    }
    if place.province:
        job["province"] = place.province
    if raw.level:
        job["level"] = raw.level[:60]
    s = summarize(raw.text)
    if s:
        job["summary"] = s
    return job, ""
