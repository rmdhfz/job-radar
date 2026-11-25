"""Shared data types. A source turns its own response format into RawJob; everything after that is source-agnostic."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser


@dataclass
class Company:
    name: str
    industry: str
    website: str = ""
    sources: list[dict] = field(default_factory=list)


@dataclass
class RawJob:
    feed: str                      # e.g. "lever:ninjavan", one per company board
    source: str                    # "greenhouse" | "lever" | "workable" | "jsonld"
    source_id: str
    company: str
    title: str
    url: str
    locations: list[str] = field(default_factory=list)
    country: str | None = None     # ISO-2 hint when the source has one
    work_type: str | None = None   # onsite | hybrid | remote | None (unknown)
    posted_at: datetime | None = None
    department: str = ""
    employment_type: str = ""
    level: str = ""
    salary_min: float | None = None  # only from structured IDR monthly fields, never parsed from free text
    salary_max: float | None = None
    text: str = ""                 # plain-text description, used for the summary and fraud checks only
    checked_at: datetime | None = None  # when the posting page was last fetched, if earlier than this run


def utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_dt(value) -> datetime | None:
    """ISO 8601 string, date string, or epoch milliseconds -> aware UTC datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    s = str(value).strip().replace("Z", "+00:00")
    try:
        return utc(datetime.fromisoformat(s))
    except ValueError:
        return None


def iso(dt: datetime) -> str:
    return utc(dt).strftime("%Y-%m-%dT%H:%M:%SZ")


class _Text(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_to_text(markup: str) -> str:
    if not markup:
        return ""
    p = _Text()
    p.feed(html.unescape(markup) if "&lt;" in markup else markup)
    text = "".join(p.out)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def summarize(text: str, limit: int = 280) -> str:
    """A short excerpt (PRD: never a full copy of the description)."""
    t = re.sub(r"\s+", " ", text or "").strip()
    if len(t) <= limit:
        return t
    cut = t[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return (cut[: end + 1] if end > limit * 0.5 else cut.rsplit(" ", 1)[0] + "…").strip()
