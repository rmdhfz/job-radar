"""A polite HTTP client: identifies itself, honours robots.txt (including Crawl-delay), spaces requests per host,
backs off on 429/5xx. Standard library only."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

USER_AGENT = "job-radar/0.1 (+https://job-radar.buitenzorg.dev)"
ROBOTS_AGENT = "job-radar"
# Hosts that rate-limit harder than their robots.txt says (observed HTTP 429 at 1 request/second, 2026-11-25).
HOST_DELAY = {"myworkdayjobs.com": 4.0}


class RobotsDisallowed(Exception):
    pass


class RateLimited(RuntimeError):
    """The host answered 429 even after waiting: stop asking it for the rest of this run."""


class Http:
    def __init__(self, min_delay: float = 1.0, timeout: float = 30, retries: int = 3):
        self.min_delay, self.timeout, self.retries = min_delay, timeout, retries
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._last: dict[str, float] = {}

    # ---- robots.txt
    def robots_for(self, url: str) -> urllib.robotparser.RobotFileParser:
        parts = urllib.parse.urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                status, body = self._raw(base + "/robots.txt", accept="text/plain")
                if status == 200:
                    rp.parse(body.decode("utf-8", "replace").splitlines())
                elif status in (401, 403):
                    rp.disallow_all = True       # conservative, same as Python's own robotparser
                else:
                    rp.allow_all = True          # 404 etc.: no rules (RFC 9309 section 2.3.1.3)
            except Exception:
                rp.disallow_all = True           # unreachable: assume complete disallow (RFC 9309 section 2.3.1.4)
            self._robots[base] = rp
        return self._robots[base]

    def allowed(self, url: str) -> bool:
        return self.robots_for(url).can_fetch(ROBOTS_AGENT, url)

    # ---- fetching
    def _wait(self, url: str):
        host = urllib.parse.urlsplit(url).netloc
        delay = next((d for suffix, d in HOST_DELAY.items() if host.endswith(suffix)), self.min_delay)
        rp = self._robots.get(f"{urllib.parse.urlsplit(url).scheme}://{host}")
        if rp is not None:
            cd = rp.crawl_delay(ROBOTS_AGENT)
            if cd:
                delay = max(delay, float(cd))
        gap = time.monotonic() - self._last.get(host, 0)
        if gap < delay:
            time.sleep(delay - gap)
        self._last[host] = time.monotonic()

    def _raw(self, url: str, accept: str = "application/json") -> tuple[int, bytes]:
        status, body, _ = self._raw3(url, accept)
        return status, body

    def _raw3(self, url: str, accept: str = "application/json") -> tuple[int, bytes, str]:
        self._wait(url)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                final = r.geturl()
                if final != url and not final.endswith("/robots.txt") and not self.allowed(final):
                    raise RobotsDisallowed(final)
                return r.status, r.read(), ""
        except urllib.error.HTTPError as e:
            return e.code, (e.read() if e.fp else b""), (e.headers.get("Retry-After", "") if e.headers else "")

    def get(self, url: str, accept: str = "application/json") -> bytes:
        if not self.allowed(url):
            raise RobotsDisallowed(url)
        for attempt in range(self.retries + 1):
            status, body, retry_after = self._raw3(url, accept)
            if status == 200:
                return body
            if status == 429:
                if attempt == 0:  # one polite wait, then give up on this host for the run
                    time.sleep(min(60, int(retry_after) if retry_after.isdigit() else 20))
                    continue
                raise RateLimited(f"HTTP 429 for {url}")
            if status in (500, 502, 503, 504) and attempt < self.retries:
                time.sleep(min(60, 5 * 2 ** attempt))
                continue
            raise RuntimeError(f"HTTP {status} for {url}")
        raise RuntimeError(f"giving up on {url}")

    def get_json(self, url: str):
        return json.loads(self.get(url).decode("utf-8"))
