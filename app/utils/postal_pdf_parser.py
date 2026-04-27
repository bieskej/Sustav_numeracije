from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


try:
    import pdfplumber  # type: ignore
except Exception:  # pragma: no cover
    pdfplumber = None


@dataclass(frozen=True)
class PostalPdfRecord:
    postanski_broj: str
    naziv_poste: str


_LINE_RE = re.compile(r"^\s*(?P<code>\d{5})\s+(?P<name>.+?)\s{2,}|^\s*(?P<code2>\d{5})\s+(?P<name2>.+)$")


def parse_spisak_posta_pdf(pdf_path: Path) -> list[PostalPdfRecord]:
    """
    Parses `Spisak-posta.pdf` which contains lines like:
      78101 Banja Luka ...
      76300 Bijeljina ...
    We keep `postanski_broj` (5 digits) and the immediate name token(s) following it
    until the schedule columns start (best-effort).
    """
    if pdfplumber is None:
        raise RuntimeError(
            "pdfplumber is not installed. Install backend/requirements.txt dependencies."
        )

    lines: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            for ln in t.splitlines():
                lines.append(ln)

    records: dict[str, str] = {}
    for ln in lines:
        m = _LINE_RE.match(ln)
        if not m:
            continue
        code = m.group("code") or m.group("code2")
        name = m.group("name") or m.group("name2") or ""
        code = (code or "").strip()
        name = " ".join(name.strip().split())
        if not code or not name:
            continue
        records[code] = name

    return [PostalPdfRecord(postanski_broj=c, naziv_poste=n) for c, n in sorted(records.items())]

