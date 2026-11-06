"""Domain layer: the read-only catalogue service.

Views stay thin: they parse the request and ask :class:`Catalogue` for data.
The service owns the search-parameter handling (validation and defaults) and
turns the low-level :mod:`app.db` queries into page-sized results.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from math import ceil

from flask import current_app

from . import db

#: Number of page links shown on each side of the current page.
_PAGE_WINDOW: int = 2


@dataclass(frozen=True)
class SearchResult:
    """One page of search results plus the data the toolbar needs."""

    filters: db.SearchFilters
    rows: list[sqlite3.Row]
    total: int
    page: int
    pages: int
    page_items: list[int | None]
    per: int
    sort: str

    @property
    def searched(self) -> bool:
        """Return ``True`` when at least one search condition was supplied."""
        return not self.filters.is_empty


def _as_int(value: str | None) -> int | None:
    """Parse an optional integer query parameter."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _page_items(page: int, pages: int) -> list[int | None]:
    """Return the page numbers to render, using ``None`` for an ellipsis gap."""
    visible: set[int] = {1, pages}
    for candidate in range(page - _PAGE_WINDOW, page + _PAGE_WINDOW + 1):
        if 1 <= candidate <= pages:
            visible.add(candidate)
    items: list[int | None] = []
    previous = 0
    for number in sorted(visible):
        if number - previous > 1:
            items.append(None)
        items.append(number)
        previous = number
    return items


class Catalogue:
    """Read-only access to the SMD catalogue, one instance per application.

    The connections themselves belong to :mod:`app.database`; this
    service only turns request parameters into queries and page-sized results.
    """

    def stats(self) -> dict[str, int]:
        """Return the catalogue size counters."""
        return db.stats()

    def search(self, args: Mapping[str, str]) -> SearchResult:
        """Run the search described by the request parameters ``args``.

        Without any condition the catalogue is not listed: the result is empty
        and page-sized so the template can show the "start a search" state.
        """
        filters = db.SearchFilters(
            code=(args.get("code") or "").strip(),
            name=(args.get("name") or "").strip(),
            function_id=_as_int(args.get("function")),
            manufacturer_id=_as_int(args.get("manufacturer")),
            package_id=(args.get("package") or "").strip(),
            pins=_as_int(args.get("pins")),
        )

        sort = args.get("sort") or db.DEFAULT_SORT
        if sort not in db.SORTS:
            sort = db.DEFAULT_SORT

        page_sizes: tuple[int, ...] = current_app.config["PAGE_SIZES"]
        default_page_size: int = current_app.config["DEFAULT_PAGE_SIZE"]

        per = _as_int(args.get("per")) or default_page_size
        if per not in page_sizes:
            per = default_page_size

        if filters.is_empty:
            return SearchResult(filters, [], 0, 1, 1, [], per, sort)

        total = db.count_parts(filters)
        pages = max(1, ceil(total / per))
        page = min(max(1, _as_int(args.get("page")) or 1), pages)
        rows = db.fetch_parts(filters, sort, per, (page - 1) * per)
        return SearchResult(
            filters, rows, total, page, pages, _page_items(page, pages), per, sort
        )

    def part(self, part_id: int) -> sqlite3.Row | None:
        """Return a single part by id, or ``None`` when it does not exist."""
        return db.get_part(part_id)

    def related(self, part: sqlite3.Row) -> list[sqlite3.Row]:
        """Return other parts that share the marking of ``part``."""
        return db.parts_with_marking(part["code"], part["id"], part["package_id"])

    def has_image(self, code: str) -> bool:
        """Return ``True`` when the package stores a real drawing."""
        return db.has_package_image(code)

    def image(self, code: str) -> bytes | None:
        """Return the PNG drawing for a package code, or ``None``."""
        return db.package_image(code)

    def menu(self) -> tuple[list[sqlite3.Row], list[sqlite3.Row], list[sqlite3.Row]]:
        """Return the search form options: functions, manufacturers, packages."""
        return db.list_functions(), db.list_manufacturers(), db.list_packages()
