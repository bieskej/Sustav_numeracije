from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

try:
    import pdfplumber  # type: ignore
except Exception:  # pragma: no cover
    pdfplumber = None


_PREFIX_LINE_RE = re.compile(
    r"(?P<prefix>0\d{2,5})\s+(?P<name>[A-Za-zČĆĐŠŽčćđšž .,'()-]{2,})"
)

_PREFIX_SLASH_RE = re.compile(
    r"(?P<prefix>0\d{2,5})[/-]\s*(?P<name>[A-Za-zČĆĐŠŽčćđšž .,'()-]{2,})"
)


@dataclass(frozen=True)
class PrefixRecord:
    prefix: str
    region_name: str


def extract_prefix_records(pdf_path: Path) -> list[PrefixRecord]:
    """
    Best-effort extractor for 'Plan numeracije' style documents where geographic
    area prefixes appear as lines like: '051 Banja Luka' or '053 Bijeljina'.

    If your PDF has a different structure, adjust `_PREFIX_LINE_RE` accordingly.
    """
    if pdfplumber is None:
        raise RuntimeError(
            "pdfplumber is not installed. Install backend/requirements.txt dependencies."
        )

    text_parts: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            if t:
                text_parts.append(t)
    text = "\n".join(text_parts)

    records: dict[str, str] = {}
    for rx in (_PREFIX_LINE_RE, _PREFIX_SLASH_RE):
        for m in rx.finditer(text):
            prefix = m.group("prefix")
            name = " ".join(m.group("name").strip().split())
            records[prefix] = name

    return [PrefixRecord(prefix=p, region_name=n) for p, n in sorted(records.items())]

