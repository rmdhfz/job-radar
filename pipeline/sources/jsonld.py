"""Company career pages that publish schema.org JobPosting JSON-LD (Tier A, PRD section 5).

Discovery is through the sitemap the site itself declares in robots.txt; every page fetch goes through Http, so
robots.txt and Crawl-delay are honoured. Works for Workday-hosted company career sites ({tenant}.myworkdayjobs.com),
whose job URLs carry the location (/job/Jakarta/...), and for any site with JobPosting markup.

companies.yaml:  {type: jsonld, sitemap: https://.../siteMap.xml, max_pages: 150}
"""
from __future__ import annotations

import html as htmllib
import json
import re
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urlsplit

from .. import geo
from ..http import RateLimited, RobotsDisallowed
from ..models import Company, RawJob, html_to_text, iso, parse_dt

CACHE_AGE = timedelta(hours=48)  # PRD section 7 wants a liveness check within 72 h; sitemap presence is checked every run

NAME = "jsonld"
LABEL = "Situs karier perusahaan"
LD = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I)


def feed(cfg: dict) -> str:
    p = urlsplit(cfg["sitemap"])
    return f"{NAME}:{p.netloc}{p.path.rsplit('/', 1)[0]}"


def parse_sitemap(xml: str) -> list[str]:
    return [htmllib.unescape(u.strip()) for u in re.findall(r"<loc>\s*([^<]+?)\s*</loc>", xml or "")]


def url_location(url: str) -> str:
    """Workday-style /job/{Location}/{Title}_{Req} -> "Location" with spaces."""
    m = re.search(r"/job/([^/]+)/", urlsplit(url).path)
    return unquote(m.group(1)).replace("-", " ").strip() if m else ""


def looks_indonesian(url: str) -> bool:
    loc = url_location(url)
    return bool(loc) and geo.resolve([loc]).indonesia


def _postings(obj):
    if isinstance(obj, list):
        for o in obj:
            yield from _postings(o)
    elif isinstance(obj, dict):
        t = obj.get("@type")
        if t == "JobPosting" or (isinstance(t, list) and "JobPosting" in t):
            yield obj
        for o in obj.get("@graph") or []:
            yield from _postings(o)


def _places(p: dict) -> list[str]:
    locs = p.get("jobLocation") or []
    out = []
    for l in locs if isinstance(locs, list) else [locs]:
        a = (l or {}).get("address") or {}
        if isinstance(a, str):
            out.append(a)
        elif isinstance(a, dict):
            country = a.get("addressCountry")
            country = country.get("name") if isinstance(country, dict) else country
            out.append(", ".join(str(x) for x in (a.get("addressLocality"), a.get("addressRegion"), country) if x))
    return [o for o in out if o]


def _salary(p: dict) -> tuple[float | None, float | None]:
    s = p.get("baseSalary") or {}
    if not isinstance(s, dict) or (s.get("currency") or "").upper() != "IDR":
        return None, None
    v = s.get("value") or {}
    if not isinstance(v, dict) or (v.get("unitText") or "").upper() != "MONTH":
        return None, None  # only explicit rupiah per month; never converted or guessed
    lo, hi = v.get("minValue", v.get("value")), v.get("maxValue", v.get("value"))
    try:
        return (float(lo) if lo else None), (float(hi) if hi else None)
    except (TypeError, ValueError):
        return None, None


def parse_page(page: str, url: str, company: Company, cfg: dict, now: datetime | None = None) -> list[RawJob]:
    now = now or datetime.now(timezone.utc)
    out = []
    for block in LD.findall(page or ""):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        for p in _postings(data):
            until = parse_dt(p.get("validThrough"))
            if until and until < now:
                continue  # the site itself says the posting has closed
            ident = p.get("identifier")
            ident = ident.get("value") if isinstance(ident, dict) else ident
            remote = str(p.get("jobLocationType") or "").upper() == "TELECOMMUTE"
            lo, hi = _salary(p)
            et = p.get("employmentType")
            out.append(RawJob(
                feed=feed(cfg), source=NAME, source_id=str(ident or url), company=company.name,
                title=htmllib.unescape(str(p.get("title") or "")).strip(), url=url,
                locations=_places(p) + [url_location(url)], work_type="remote" if remote else None,
                posted_at=parse_dt(p.get("datePosted")), employment_type=", ".join(et) if isinstance(et, list) else str(et or ""),
                salary_min=lo, salary_max=hi, text=html_to_text(str(p.get("description") or ""))))
    return out


def _thaw(d: dict) -> RawJob:
    d = dict(d)
    for k in ("posted_at", "checked_at"):
        d[k] = parse_dt(d.get(k))
    return RawJob(**d)


def _freeze(r: RawJob) -> dict:
    d = asdict(r)
    for k in ("posted_at", "checked_at"):
        d[k] = iso(d[k]) if d[k] else None
    return d


def fetch(cfg: dict, company: Company, http, store=None, now: datetime | None = None) -> list[RawJob]:
    """A page still in the sitemap and fetched within CACHE_AGE is reused (with its real check time) instead of
    refetched, so each run mostly asks the site for new postings only. A 429 aborts the board for this run: it is
    reported as failed, which keeps its jobs instead of expiring them."""
    now = now or datetime.now(timezone.utc)
    urls = [u for u in parse_sitemap(http.get(cfg["sitemap"], accept="application/xml").decode("utf-8", "replace")) if looks_indonesian(u)]
    jobs: list[RawJob] = []
    for u in urls[: int(cfg.get("max_pages", 150))]:
        hit = store.page_get(u, now, CACHE_AGE) if store else None
        if hit:
            fetched_at, cached = hit
            for d in cached:
                r = _thaw(d)
                r.checked_at = parse_dt(fetched_at)
                jobs.append(r)
            continue
        try:
            found = parse_page(http.get(u, accept="text/html").decode("utf-8", "replace"), u, company, cfg, now)
        except RateLimited:
            raise
        except (RobotsDisallowed, RuntimeError):
            continue  # a single dead or disallowed page is skipped; it is simply not "seen" this run
        if store:
            store.page_put(u, now, [_freeze(r) for r in found])
        jobs += found
    return jobs
