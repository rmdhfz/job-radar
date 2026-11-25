"""Extends the CITIES gazetteer in index.html with Indonesian towns from GeoNames (cities15000, CC BY 4.0).
Only writes between /*GAZ:START*/ and /*GAZ:END*/; the hand-curated CITIES above it always win.

    curl -O https://download.geonames.org/export/dump/cities15000.zip
    curl -O https://download.geonames.org/export/dump/admin1CodesASCII.txt
    python -I tools/build_gazetteer.py cities15000.zip admin1CodesASCII.txt [--dry-run]

Rules: population >= 15,000 (the file's own cut), not a "section of a populated place" (PPLX), at least 10 km from any
city already in the gazetteer (so Jakarta districts and suburbs do not become separate bars), names that are also
common words are skipped, coordinates rounded to 3 decimals (~100 m).
"""
import json
import math
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROVINCES = {
    "Aceh": "Aceh", "Bali": "Bali", "Bangka–Belitung Islands": "Kep. Bangka Belitung", "Banten": "Banten", "Bengkulu": "Bengkulu",
    "Central Java": "Jawa Tengah", "Central Kalimantan": "Kalimantan Tengah", "Central Papua": "Papua Tengah",
    "Central Sulawesi": "Sulawesi Tengah", "East Java": "Jawa Timur", "East Kalimantan": "Kalimantan Timur",
    "East Nusa Tenggara": "Nusa Tenggara Timur", "Gorontalo": "Gorontalo", "Highland Papua": "Papua Pegunungan",
    "Jakarta": "DKI Jakarta", "Jambi": "Jambi", "Lampung": "Lampung", "Maluku": "Maluku", "North Kalimantan": "Kalimantan Utara",
    "North Maluku": "Maluku Utara", "North Sulawesi": "Sulawesi Utara", "North Sumatra": "Sumatera Utara", "Papua": "Papua",
    "Riau": "Riau", "Riau Islands": "Kepulauan Riau", "South Kalimantan": "Kalimantan Selatan", "South Papua": "Papua Selatan",
    "South Sulawesi": "Sulawesi Selatan", "South Sumatra": "Sumatera Selatan", "Southeast Sulawesi": "Sulawesi Tenggara",
    "Southwest Papua": "Papua Barat Daya", "West Java": "Jawa Barat", "West Kalimantan": "Kalimantan Barat",
    "West Nusa Tenggara": "Nusa Tenggara Barat", "West Papua": "Papua Barat", "West Sulawesi": "Sulawesi Barat",
    "West Sumatra": "Sumatera Barat", "Yogyakarta": "DI Yogyakarta",
}
# names that are also ordinary words in job titles or locations; matching them would misplace jobs
STOP = {"kota", "baru", "barat", "timur", "utara", "selatan", "tengah", "raya", "jaya", "pusat", "area", "sales", "soe", "ende", "tual", "raha",
        "negara", "batu", "bandar", "sumber", "simpang", "tanjung", "metro", "labuan", "nusantara", "banjar", "panji", "pare"}
SKIP = {"South Tangerang"}  # already an alias of Tangerang in pipeline/geo.py
MARK = re.compile(r"/\*GAZ:START\*/.*?/\*GAZ:END\*/", re.S)


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[1], a[0], b[1], b[0]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def main(zip_path, admin_path, dry=False):
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    curated = json.loads(re.search(r"const CITIES = (\{.*?\});", html, re.S).group(1))
    admin = {}
    for line in Path(admin_path).read_text(encoding="utf-8").splitlines():
        code, name = line.split("\t")[:2]
        if code.startswith("ID."):
            admin[code[3:]] = name
    rows = [l.split("\t") for l in zipfile.ZipFile(zip_path).read("cities15000.txt").decode("utf-8").splitlines()]
    rows = sorted((r for r in rows if r[8] == "ID" and r[7] != "PPLX"), key=lambda r: -int(r[14] or 0))  # biggest first
    taken = {k: (v[0], v[1]) for k, v in curated.items()}
    lower = {k.lower() for k in curated}
    added, missing_prov = {}, set()
    for r in rows:
        name, lat, lng = r[1].strip(), float(r[4]), float(r[5])
        if name.lower() in lower or name.lower() in STOP or name in SKIP or len(name) < 4:
            continue
        if any(km((lng, lat), p) < 10 for p in taken.values()):
            continue
        prov = PROVINCES.get(admin.get(r[10], ""))
        if not prov:
            missing_prov.add(admin.get(r[10], r[10]))
            continue
        added[name] = [round(lng, 3), round(lat, 3), prov]
        taken[name] = (lng, lat)
        lower.add(name.lower())
    if missing_prov:
        raise SystemExit(f"unmapped provinces: {sorted(missing_prov)}")
    block = "/*GAZ:START*/Object.assign(CITIES," + json.dumps(dict(sorted(added.items())), ensure_ascii=False, separators=(",", ":")) + \
            "); // GeoNames cities15000 (CC BY 4.0), tools/build_gazetteer.py/*GAZ:END*/"
    print(f"{len(added)} towns added, {len(block)} bytes")
    if dry:
        print(", ".join(sorted(added)))
        return
    if not MARK.search(html):
        raise SystemExit("GAZ markers not found in index.html")
    (ROOT / "index.html").write_text(MARK.sub(lambda m: block, html), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    main(a[0], a[1], "--dry-run" in sys.argv)
