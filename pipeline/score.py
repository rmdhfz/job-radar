"""Trust score, PRD section 7. Every point has to be earned by something the pipeline actually observed."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

FEE = re.compile(r"biaya\s+(pendaftaran|administrasi|pelatihan|seragam|medical|tes)|uang\s+(administrasi|jaminan|pendaftaran|muka)|"
                 r"transfer\s+(dana|uang|biaya)|registration\s+fee|processing\s+fee|training\s+fee|pay\s+a\s+fee", re.I)
PRIVATE_CHAT = re.compile(r"wa\.me/|api\.whatsapp\.com|whatsapp\s*(ke|only|saja)|t\.me/(?!s/)", re.I)
FREE_MAIL = re.compile(r"[\w.+-]+@(gmail|yahoo|ymail|hotmail|outlook|live)\.(com|co\.id)", re.I)


def registrable(host: str) -> str:
    parts = (host or "").lower().split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "or", "ac", "go", "web", "my", "com", "net"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def trust(*, official: bool, verified_now: bool, complete: bool, url: str, website: str, text: str) -> tuple[int, list[str]]:
    score, why = 0, []
    if official:
        score += 40; why.append("+40 sumber resmi (ATS publik atau domain perusahaan)")
    if verified_now:
        score += 20; why.append("+20 masih tayang di sumber resmi pada pengambilan terakhir")
    if complete:
        score += 10; why.append("+10 data lengkap")
    if url and website and registrable(urlsplit(url).hostname or "") == registrable(urlsplit(website).hostname or ""):
        score += 15; why.append("+15 domain tautan lamar = domain perusahaan")
    if FEE.search(text or ""):
        score -= 50; why.append("-50 menyebut biaya/transfer")
    if PRIVATE_CHAT.search(text or "") and not url:
        score -= 30; why.append("-30 hanya kontak chat pribadi")
    if FREE_MAIL.search(text or ""):
        score -= 20; why.append("-20 email gratisan")
    return max(0, min(100, score)), why
