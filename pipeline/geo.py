"""Location text -> gazetteer city. The gazetteer is read from CITIES in index.html so portal and pipeline never disagree."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Common spellings that are not gazetteer keys. Only map to a city when it is the same place or its metro area.
ALIASES = {
    "dki jakarta": "Jakarta", "greater jakarta": "Jakarta", "jabodetabek": "Jakarta",
    "jakarta selatan": "Jakarta", "south jakarta": "Jakarta", "jakarta pusat": "Jakarta", "central jakarta": "Jakarta",
    "jakarta barat": "Jakarta", "west jakarta": "Jakarta", "jakarta timur": "Jakarta", "east jakarta": "Jakarta",
    "jakarta utara": "Jakarta", "north jakarta": "Jakarta", "jkt": "Jakarta",
    "tangerang selatan": "Tangerang", "south tangerang": "Tangerang", "tangsel": "Tangerang", "bsd": "Tangerang",
    "bsd city": "Tangerang", "serpong": "Tangerang", "bali": "Denpasar", "badung": "Denpasar", "kuta": "Denpasar",
    "jogja": "Yogyakarta", "jogjakarta": "Yogyakarta", "yogya": "Yogyakarta", "sleman": "Yogyakarta",
    "cibitung": "Cikarang", "jababeka": "Cikarang", "batam island": "Batam",
    # regency or common name -> its seat in the GeoNames part of the gazetteer
    "solo": "Surakarta", "buleleng": "Singaraja", "sumbawa": "Sumbawa Besar",
}
COUNTRIES = re.compile(r"\b(malaysia|singapore|philippines|thailand|vietnam|india|china|hong kong|taiwan|japan|korea|"
                       r"australia|united states|usa|united kingdom|uk|germany|france|netherlands|uae|dubai|brazil|mexico)\b", re.I)


@dataclass
class Place:
    indonesia: bool
    city: str | None = None
    province: str = ""
    remote: bool = False


@lru_cache(maxsize=1)
def cities() -> dict[str, list]:
    text = (ROOT / "index.html").read_text(encoding="utf-8")
    m = re.search(r"const CITIES = (\{.*?\});", text, re.S)
    if not m:
        raise RuntimeError("CITIES gazetteer not found in index.html")
    out = json.loads(m.group(1))
    g = re.search(r"/\*GAZ:START\*/Object\.assign\(CITIES,(\{.*?\})\);", text, re.S)  # GeoNames towns, curated entries win
    if g:
        for k, v in json.loads(g.group(1)).items():
            out.setdefault(k, v)
    return out


@lru_cache(maxsize=1)
def _patterns() -> list[tuple[re.Pattern, str]]:
    names = {k.lower(): k for k in cities()}
    names.update({k: v for k, v in ALIASES.items() if v in cities()})
    # longest first, so "jakarta selatan" wins over "jakarta"
    return [(re.compile(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", re.I), v) for k, v in sorted(names.items(), key=lambda kv: -len(kv[0]))]


def find_city(text: str) -> str | None:
    for pat, city in _patterns():
        if pat.search(text or ""):
            return city
    return None


def resolve(locations: list[str], country: str | None = None, title: str = "") -> Place:
    """Pick the first Indonesian location. Parts that name another country are ignored."""
    any_id = False
    remote = False
    for raw in locations:
        for part in re.split(r"[;|/]", raw or ""):
            p = part.strip()
            if not p:
                continue
            says_id = bool(re.search(r"\bindonesia\b|\bidn?\b", p, re.I))
            if COUNTRIES.search(p) and not says_id:
                continue
            city = find_city(p)
            is_id = says_id or city is not None or (country or "").upper() in ("ID", "IDN", "INDONESIA")
            if not is_id:
                continue
            any_id = True
            if re.search(r"\bremote\b", p, re.I):
                remote = True
            if city:
                return Place(True, city, cities()[city][2], remote)
    if any_id:
        city = find_city(title)  # e.g. "Business Development Executive (Surabaya)"
        if city:
            return Place(True, city, cities()[city][2], remote)
    return Place(any_id, None, "", remote)
