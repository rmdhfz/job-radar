"""SQLite store (PRD section 8). Tracks when each job was first/last seen so jobs can expire honestly:
a job that is missing from a board that was fetched successfully counts one missed cycle; after 2 it is expired
(PRD section 7). A board that failed to fetch never expires its jobs."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta

from .models import iso

SCHEMA = """
create table if not exists jobs(
  id text primary key, feed text not null, data text not null,
  first_seen text not null, last_seen text not null, missing integer not null default 0);
create index if not exists jobs_feed on jobs(feed);
create table if not exists pages(url text primary key, fetched_at text not null, jobs text not null);
create table if not exists runs(
  at text not null, feed text not null, ok integer not null, fetched integer, kept integer, skipped text, error text);
"""


class Store:
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)

    def record(self, feed: str, jobs: list[dict], now: datetime):
        ts = iso(now)
        seen = set()
        for j in jobs:
            seen.add(j["id"])
            self.db.execute(
                "insert into jobs(id, feed, data, first_seen, last_seen, missing) values(?,?,?,?,?,0) "
                "on conflict(id) do update set data=excluded.data, last_seen=excluded.last_seen, missing=0",
                (j["id"], feed, json.dumps(j, ensure_ascii=False), ts, ts))
        for (jid,) in self.db.execute("select id from jobs where feed=?", (feed,)).fetchall():
            if jid not in seen:
                self.db.execute("update jobs set missing=missing+1 where id=?", (jid,))
        self.db.commit()

    def page_get(self, url: str, now: datetime, max_age: timedelta):
        row = self.db.execute("select fetched_at, jobs from pages where url=?", (url,)).fetchone()
        if row and now - datetime.fromisoformat(row[0].replace("Z", "+00:00")) < max_age:
            return row[0], json.loads(row[1])
        return None

    def page_put(self, url: str, now: datetime, jobs: list[dict]):
        self.db.execute("insert or replace into pages values(?,?,?)", (url, iso(now), json.dumps(jobs, ensure_ascii=False)))
        self.db.commit()

    def retire(self, configured_feeds: set[str]):
        """A board removed from companies.yaml: its jobs age out like missing ones."""
        for (feed,) in self.db.execute("select distinct feed from jobs").fetchall():
            if feed not in configured_feeds:
                self.db.execute("update jobs set missing=missing+1 where feed=?", (feed,))
        self.db.commit()

    def log(self, now: datetime, feed: str, ok: bool, fetched=0, kept=0, skipped=None, error=""):
        self.db.execute("insert into runs values(?,?,?,?,?,?,?)", (iso(now), feed, int(ok), fetched, kept, json.dumps(skipped or {}), error))
        self.db.commit()

    def active(self) -> list[dict]:
        """Jobs to export: seen in the latest successful fetch (active) or missed once (unverified)."""
        out = []
        for data, missing in self.db.execute("select data, missing from jobs where missing < 2 order by id"):
            j = json.loads(data)
            if missing:
                j["status"] = "unverified"
                j["trust"] = max(0, j["trust"] - 20)  # the +20 for "still listed" no longer holds
            out.append(j)
        return out

    def purge(self, now: datetime, days: int = 30):
        """PRD: drop jobs expired for more than 30 days."""
        self.db.execute("delete from jobs where missing >= 2 and last_seen < ?", (iso(now - timedelta(days=days)),))
        self.db.commit()
