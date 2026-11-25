"""Parser and pipeline tests against saved real responses (tests/fixtures, see its README). No network."""
import json
import urllib.robotparser
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema
import pytest

from pipeline import geo
from pipeline.models import Company
from pipeline.normalize import normalize
from pipeline.run import collect, export, load_companies, write_if_changed
from pipeline.score import trust
from pipeline.sources import greenhouse, lever, workable
from pipeline.store import Store

FIX = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 11, 25, 6, 0, tzinfo=timezone.utc)


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def kept(mod, fixture, company, cfg):
    jobs, skipped = [], {}
    for r in mod.parse(load(fixture), company, cfg):
        j, why = normalize(r, company, mod.LABEL, NOW)
        if j:
            jobs.append(j)
        else:
            skipped[why] = skipped.get(why, 0) + 1
    return jobs, skipped


# ---------------------------------------------------------------- geo
@pytest.mark.parametrize("locs,country,title,city", [
    (["Jakarta, Indonesia"], None, "", "Jakarta"),
    (["South Jakarta, South Jakarta City, Indonesia"], None, "", "Jakarta"),
    (["Bali, Indonesia", "Bangkok, Thailand"], None, "", "Denpasar"),
    (["Kuala Lumpur, Malaysia", "Jakarta, Indonesia"], None, "", "Jakarta"),
    (["Jakarta"], "ID", "", "Jakarta"),
    (["Central Java, Indonesia"], "ID", "Business Development Executive (Surabaya)", "Surabaya"),
])
def test_resolve_city(locs, country, title, city):
    assert geo.resolve(locs, country, title).city == city


def test_resolve_outside_and_unknown():
    assert not geo.resolve(["Kuala Lumpur, Malaysia"]).indonesia
    assert not geo.resolve(["Bangalore, India "]).indonesia
    p = geo.resolve(["Central Java, Indonesia"], "ID", "Business Development Executive")
    assert p.indonesia and p.city is None
    assert geo.resolve(["Central Java, Indonesia"], "ID", "Business Development Executive (Purwokerto)").city == "Purwokerto"  # GeoNames part
    assert geo.resolve(["Solo, Central Java, Indonesia"]).city == "Surakarta"
    assert geo.find_city("Badan Usaha Milik Negara") is None      # "Negara" is a town but also a word: never matched
    r = geo.resolve(["Indonesia (Remote)"])
    assert r.indonesia and r.remote and r.city is None


def test_gazetteer_comes_from_index_html():
    assert geo.cities()["Balikpapan"][2] == "Kalimantan Timur"


# ---------------------------------------------------------------- sources
XENDIT = Company("Xendit", "Perbankan & Keuangan", "https://www.xendit.co")


def test_greenhouse_xendit():
    jobs, skipped = kept(greenhouse, "greenhouse_xendit.json", XENDIT, {"board": "xendit"})
    titles = {j["title"]: j for j in jobs}
    sam = titles["Strategic Account Manager"]
    assert sam["city"] == "Jakarta" and sam["province"] == "DKI Jakarta"
    assert sam["url"].startswith("https://") and sam["posted_at"].endswith("Z")
    assert "Customer Success Manager (TH)" not in titles          # Bangkok only
    assert skipped.get("outside-id", 0) > 0
    assert all(j["salary_min"] is None for j in jobs)             # Greenhouse list has no pay: never guessed
    assert all(len(j.get("summary", "")) <= 281 for j in jobs)    # an excerpt, not the description


def test_lever_ninjavan_and_lalamove():
    nv = Company("Ninja Van", "Logistik & Pelayaran", "https://www.ninjavan.co")
    jobs, skipped = kept(lever, "lever_ninjavan.json", nv, {"site": "ninjavan"})
    by = {j["title"]: j for j in jobs}
    sby = by["Business Development Executive (Surabaya)"]
    assert sby["city"] == "Surabaya" and sby["work_type"] == "hybrid"
    assert by["Business Development Executive (Purwokerto)"]["province"] == "Jawa Tengah"   # city from the title
    assert skipped["outside-id"] == 5
    lm = Company("Lalamove", "Logistik & Pelayaran", "https://www.lalamove.com")
    jobs, _ = kept(lever, "lever_lalamove.json", lm, {"site": "lalamove"})
    assert {"Jakarta", "Bandung", "Palembang"} <= {j["city"] for j in jobs}


def test_workable_ajaib_and_amartha():
    aj = Company("Ajaib", "Perbankan & Keuangan", "https://ajaib.co.id")
    jobs, _ = kept(workable, "workable_ajaib.json", aj, {"account": "ajaib"})
    be = next(j for j in jobs if j["title"] == "Backend Engineer - Money")
    assert be["city"] == "Jakarta" and be["level"] == "Associate" and be["work_type"] == "remote"
    assert be["url"] == "https://apply.workable.com/j/5E5FADBEA0"
    am = Company("Amartha", "Perbankan & Keuangan", "https://amartha.com")
    jobs, skipped = kept(workable, "workable_amartha.json", am, {"account": "amartha"})
    assert jobs and all(j["city"] in geo.cities() or (j["city"] == "Remote" and j["work_type"] == "remote") for j in jobs)
    assert skipped.get("unknown-city", 0) > 0                      # small towns are reported, not misplaced
    pool = next(j for j in jobs if j["title"].startswith("(Talent Pool) Business Manager - Nusa Tenggara Barat"))
    assert pool["city"] == "Remote" and pool["trust"] == 60        # no city: not "complete", so not verified


# ---------------------------------------------------------------- trust (PRD section 7)
def test_trust_rules():
    base = dict(official=True, verified_now=True, complete=True, website="https://www.ninjavan.co")
    s, _ = trust(url="https://jobs.lever.co/ninjavan/1", text="", **base)
    assert s == 70                                               # earns "Terverifikasi", nothing more
    s, _ = trust(url="https://careers.ninjavan.co/1", text="", **base)
    assert s == 85                                               # apply link on the company's own domain
    s, _ = trust(url="https://jobs.lever.co/x/1", text="Peserta wajib membayar biaya pendaftaran Rp 250.000", **base)
    assert s < 40                                                # fee request: never verified
    s, _ = trust(url="https://jobs.lever.co/x/1", text="Kirim CV ke hrd.rekrut@gmail.com", **base)
    assert s == 50


# ---------------------------------------------------------------- store: honest expiry
def test_expiry_after_two_missed_cycles_but_not_on_failure():
    st = Store()
    j = {"id": "lever-1", "trust": 70, "status": "active", "title": "x"}
    st.record("lever:a", [j], NOW)
    assert st.active()[0]["status"] == "active"
    st.record("lever:a", [], NOW + timedelta(hours=3))           # missed once
    a = st.active()
    assert a[0]["status"] == "unverified" and a[0]["trust"] == 50
    st.record("lever:a", [], NOW + timedelta(hours=6))           # missed twice: expired
    assert st.active() == []
    st.record("lever:b", [dict(j, id="lever-2")], NOW)
    # a failed fetch simply does not call record(): lever-2 stays active
    assert [x["id"] for x in st.active()] == ["lever-2"]


# ---------------------------------------------------------------- end to end, offline
class FixtureHttp:
    MAP = {"boards-api.greenhouse.io/v1/boards/xendit/": "greenhouse_xendit.json", "api.lever.co/v0/postings/ninjavan": "lever_ninjavan.json",
           "api.lever.co/v0/postings/lalamove": "lever_lalamove.json", "accounts/ajaib": "workable_ajaib.json", "accounts/amartha": "workable_amartha.json"}

    def get_json(self, url):
        for k, f in self.MAP.items():
            if k in url:
                return load(f)
        raise RuntimeError("HTTP 404 for " + url)                 # boards without a fixture behave like a failed fetch


def test_end_to_end_export_matches_schema(tmp_path):
    companies = load_companies()
    st = Store()
    report = collect(companies, FixtureHttp(), st, NOW)
    doc = export(st, companies, report, NOW)
    jsonschema.validate(doc, json.loads((ROOT / "schema" / "jobs.schema.json").read_text(encoding="utf-8")))
    jobs = doc["jobs"]
    assert len(jobs) > 30
    assert len({j["id"] for j in jobs}) == len(jobs)
    assert all(j["city"] in geo.cities() or j["city"] == "Remote" for j in jobs)
    assert all(j["status"] == "active" for j in jobs)
    assert all(j["trust"] >= 70 for j in jobs if j["city"] != "Remote")      # official + still listed + complete
    assert {r["feed"]: r["ok"] for r in report}["lever:nium"] is False  # no fixture -> reported as failed, not hidden
    assert set(doc["companies"]) == {c.name for c in companies}
    out = tmp_path / "jobs.json"
    assert write_if_changed(out, doc, NOW) is True
    later = export(st, companies, report, NOW + timedelta(hours=3))
    assert write_if_changed(out, later, NOW + timedelta(hours=3)) is False   # only timestamps changed
    assert write_if_changed(out, later, NOW + timedelta(hours=21)) is True   # but refreshed at least daily


def test_companies_yaml_has_no_tier_c_or_disallowed_sources():
    text = (ROOT / "pipeline" / "companies.yaml").read_text(encoding="utf-8").lower()
    body = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
    for banned in ("linkedin", "jobstreet", "indeed", "kalibrr", "smartrecruiters"):
        assert banned not in body


def test_robots_rules_are_honoured():
    from pipeline.http import ROBOTS_AGENT
    rp = urllib.robotparser.RobotFileParser()
    rp.parse("User-agent: LinkedInBot\nAllow: /v1/companies/\nUser-agent: *\nDisallow: /".splitlines())  # api.smartrecruiters.com today
    assert not rp.can_fetch(ROBOTS_AGENT, "https://api.smartrecruiters.com/v1/companies/grab/postings")


# ---------------------------------------------------------------- company career sites (JSON-LD)
from pipeline.sources import jsonld  # noqa: E402


def test_jsonld_sitemap_filter_uses_gazetteer():
    tiket = jsonld.parse_sitemap((FIX / "workday_tiket_sitemap.xml").read_text(encoding="utf-8"))
    assert len(tiket) == 28
    keep = [u for u in tiket if jsonld.looks_indonesian(u)]
    assert keep and all("/job/Japan" not in u and "/job/Hong-Kong" not in u for u in keep)
    pwc = jsonld.parse_sitemap((FIX / "workday_pwc_sitemap.xml").read_text(encoding="utf-8"))
    assert sum(jsonld.looks_indonesian(u) for u in pwc) == 82        # /job/Jakarta/..., /job/Surabaya/...
    assert not jsonld.looks_indonesian("https://pwc.wd3.myworkdayjobs.com/Global_Experienced_Careers/job/Hyderabad/x_1")


@pytest.mark.parametrize("page,url,title,company", [
    ("workday_tiket_job_R-3422.html", "https://tiketdotcom.wd3.myworkdayjobs.com/Tiket_Careers/job/Jakarta-Indonesia/Accounting-Officer_R-3422",
     "Accounting Sr Officer", "tiket.com"),
    ("workday_pwc_job_jakarta.html", "https://pwc.wd3.myworkdayjobs.com/Global_Experienced_Careers/job/Jakarta/Supply-Chain---Logistics-Transformation-Manager--Consulting-_776266WD",
     "Supply Chain & Logistics Transformation Manager (Consulting)", "PwC Indonesia"),
])
def test_jsonld_job_page(page, url, title, company):
    co = Company(company, "Lainnya", "https://example.com")
    raws = jsonld.parse_page((FIX / page).read_text(encoding="utf-8"), url, co, {"sitemap": "https://x.example/s/siteMap.xml"}, NOW)
    assert len(raws) == 1 and raws[0].title == title and raws[0].posted_at is not None
    j, why = normalize(raws[0], co, jsonld.LABEL, NOW)
    assert j["city"] == "Jakarta" and j["trust"] == 70 and j["url"] == url and j["salary_min"] is None


def test_jsonld_skips_closed_postings():
    page = '<script type="application/ld+json">{"@context":"https://schema.org","@type":"JobPosting","title":"X",' \
           '"datePosted":"2026-10-01","validThrough":"2026-11-01T00:00:00Z"}</script>'   # synthetic markup, not a job record
    assert jsonld.parse_page(page, "https://x.example/job/Jakarta/x", XENDIT, {"sitemap": "https://x.example/s/siteMap.xml"}, NOW) == []


class SiteHttp:
    """Serves the saved tiket sitemap and job page; counts page requests; can answer 429 like Workday did."""
    def __init__(self, rate_limited=False):
        self.pages, self.rate_limited = 0, rate_limited

    def get(self, url, accept=""):
        from pipeline.http import RateLimited
        if url.endswith("siteMap.xml"):
            return (FIX / "workday_tiket_sitemap.xml").read_bytes()
        if self.rate_limited:
            raise RateLimited("HTTP 429 for " + url)
        self.pages += 1
        return (FIX / "workday_tiket_job_R-3422.html").read_bytes()


def test_jsonld_page_cache_and_rate_limit():
    from pipeline.http import RateLimited
    co, cfg, st = Company("tiket.com", "Retail & E-commerce", "https://www.tiket.com"), {"sitemap": "https://t.example/T/siteMap.xml"}, Store()
    h = SiteHttp()
    first = jsonld.fetch(cfg, co, h, st, NOW)
    n = h.pages
    assert n == 19 and len(first) == 19
    again = jsonld.fetch(cfg, co, h, st, NOW + timedelta(hours=3))
    assert h.pages == n and len(again) == 19                        # nothing refetched within 48 h
    j, _ = normalize(again[0], co, jsonld.LABEL, NOW + timedelta(hours=3))
    assert j["last_verified_at"] == "2026-11-25T06:00:00Z"          # the real check time, not the run time
    jsonld.fetch(cfg, co, h, st, NOW + timedelta(hours=49))
    assert h.pages == 2 * n                                          # stale after 48 h: refetched
    with pytest.raises(RateLimited):
        jsonld.fetch(cfg, co, SiteHttp(rate_limited=True), Store(), NOW)
