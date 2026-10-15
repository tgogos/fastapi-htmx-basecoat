"""Shared page-size choices for HTML list panels."""

from __future__ import annotations

PAGE_SIZES = (10, 25, 50, 100)
DEFAULT_PAGE_SIZE = 10


def page_size(size: int) -> int:
    if size in PAGE_SIZES:
        return size
    return DEFAULT_PAGE_SIZE


def page_window(page: int, total_pages: int) -> list[int | None]:
    """Page numbers to render. None is an ellipsis.

    Five pages or fewer show every number. A longer list shows 1 2 3 4 … last
    near the start, 1 … current−1 current current+1 … last in the middle, and
    1 … last−3 last−2 last−1 last near the end.
    """
    if total_pages < 1:
        return []
    current = min(max(page, 1), total_pages)
    if total_pages <= 5:
        return list(range(1, total_pages + 1))
    if current <= 3:
        return [1, 2, 3, 4, None, total_pages]
    if current >= total_pages - 2:
        return [1, None, total_pages - 3, total_pages - 2, total_pages - 1, total_pages]
    return [1, None, current - 1, current, current + 1, None, total_pages]


def sort_column_state(ordering: str, column: str) -> str | None:
    """Return asc, desc, or None for a table header."""
    if ordering == column:
        return "asc"
    if ordering == f"-{column}":
        return "desc"
    return None
