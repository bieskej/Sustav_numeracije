from __future__ import annotations

import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class PostalRecord:
    postanski_broj: str
    naziv_poste: str
    opcina_guess: str | None = None


_CODE_RE = re.compile(r"\b(\d{5})\b")


def fetch_cybo_rs_postal_codes(timeout_s: float = 30.0) -> list[PostalRecord]:
    """
    Scrapes the RS-only Cybo page (already scoped to Republika Srpska).
    The HTML structure may change; parser is defensive.
    """
    url = "https://xn--potanske-brojeve-med.cybo.com/bosna-i-hercegovina/republika-srpska/#listcodes"
    with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
        html = client.get(url).text

    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n")

    records: dict[str, str] = {}
    for line in (ln.strip() for ln in text.splitlines()):
        if not line:
            continue
        m = _CODE_RE.search(line)
        if not m:
            continue
        code = m.group(1)
        name = " ".join(_CODE_RE.sub("", line).strip(" -–—").split())
        if not name:
            continue
        records[code] = name

    return [PostalRecord(postanski_broj=c, naziv_poste=n) for c, n in sorted(records.items())]

