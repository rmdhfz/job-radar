"""One module per source, same interface (PRD section 8):

    url(cfg) -> str                          the single public endpoint to fetch for one company board
    parse(data, company, cfg) -> [RawJob]    pure function, unit-tested against saved real responses
    feed(cfg) -> str                         stable key for the board, e.g. "lever:ninjavan"
    LABEL                                    shown to users in source_label
    fetch(cfg, company, http) -> [RawJob]    optional, for sources that need more than one request (jsonld)

Only Tier A sources live here. Never add LinkedIn, Indeed, Jobstreet, Kalibrr or similar (AGENTS.md hard rule 1).
SmartRecruiters is deliberately absent: api.smartrecruiters.com/robots.txt disallows all agents except LinkedInBot.
"""
from . import greenhouse, jsonld, lever, workable

SOURCES = {m.NAME: m for m in (greenhouse, lever, workable, jsonld)}
