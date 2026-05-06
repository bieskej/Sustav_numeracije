from __future__ import annotations

import re
import unicodedata


_WS_RE = re.compile(r"\s+")


def normalize_name(value: str) -> str:
    """
    Deterministic normalization for municipality/location/operator names.
    - trims
    - collapses whitespace
    - unicode NFKD fold + strip diacritics
    - lowercase
    """
    v = _WS_RE.sub(" ", (value or "").strip())
    v = unicodedata.normalize("NFKD", v)
    v = "".join(ch for ch in v if not unicodedata.combining(ch))
    return v.casefold()


def digits_only(value: str) -> str:
    v = (value or "").strip()
    if not v.isdigit():
        raise ValueError("Mora sadržavati samo znamenke")
    return v


def strip_international_prefix(value: str) -> str:
    """Strip +387 or 00387 BiH international prefix, returning the national number."""
    v = (value or "").strip()
    if v.startswith("+387"):
        v = v[4:]
    elif v.startswith("00387"):
        v = v[5:]
    return v

