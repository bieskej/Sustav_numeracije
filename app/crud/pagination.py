from __future__ import annotations


def page_envelope(*, total: int, page: int, per_page: int, data: list[dict]) -> dict:
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "data": data,
    }

