"""Consistent pagination, filtering and sorting for every list route."""
from __future__ import annotations

from fastapi import Request


def parse(request: Request, default_sort: str = "created_at", default_order: str = "desc"):
    try:
        page = max(1, int(request.query_params.get("page", "1")))
    except ValueError:
        page = 1
    try:
        size = min(100, max(1, int(request.query_params.get("page_size", "20"))))
    except ValueError:
        size = 20
    order = "asc" if request.query_params.get("order", default_order).lower() == "asc" else "desc"
    sort = request.query_params.get("sort", default_sort)
    return page, size, sort, order


def order_clause(sort: str, allowed: dict[str, str], default: str, order: str) -> str:
    column = allowed.get(sort, default)
    return f"{column} {'ASC' if order == 'asc' else 'DESC'}"


def envelope(items: list, total: int, page: int, size: int) -> dict:
    return {"items": items, "total": total, "page": page, "page_size": size}
