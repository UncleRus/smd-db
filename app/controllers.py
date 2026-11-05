"""CherryPy controllers (routes) and the custom error page for SMD-DB."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from math import ceil
from typing import Any, TypeVar, cast

import cherrypy

from . import db, i18n
from .rendering import page_context, query_args, render

#: Number of page links shown on each side of the current page.
_PAGE_WINDOW: int = 2

_F = TypeVar("_F", bound=Callable[..., Any])


def expose(func: _F) -> _F:
    """Typed wrapper around :func:`cherrypy.expose`.

    CherryPy ships no type information, so its decorator would make every
    controller method ``Any``. This wrapper keeps the function signature.
    """
    return cast(_F, cherrypy.expose(func))


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


class Root:
    """Root controller: search, part detail, package image and About page.

    Every exposed method accepts ``**kwargs`` because CherryPy's default
    dispatcher rejects query-string parameters that do not match the method
    signature. The application reads the query string itself, so the keyword
    arguments are intentionally ignored.
    """

    @expose
    def index(self, **kwargs: str) -> str:
        """Render the search form and one page of results."""
        args = query_args()
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

        per = _as_int(args.get("per")) or db.DEFAULT_PAGE_SIZE
        if per not in db.PAGE_SIZES:
            per = db.DEFAULT_PAGE_SIZE

        # Without any search condition the whole catalogue must not be listed;
        # the page then shows only the form and an invitation to start a search.
        searched = not filters.is_empty
        rows: list[sqlite3.Row]
        page_items: list[int | None]
        if searched:
            total = db.count_parts(filters)
            pages = max(1, ceil(total / per))
            page = min(max(1, _as_int(args.get("page")) or 1), pages)
            rows = db.fetch_parts(filters, sort, per, (page - 1) * per)
            page_items = _page_items(page, pages)
        else:
            total = 0
            pages = 1
            page = 1
            rows = []
            page_items = []

        context = page_context("search", "main.search")
        context.update(
            filters=filters,
            searched=searched,
            rows=rows,
            total=total,
            page=page,
            pages=pages,
            page_items=page_items,
            per=per,
            sort=sort,
            functions=db.list_functions(),
            manufacturers=db.list_manufacturers(),
            packages=db.list_packages(),
        )
        return render("search.html", context)

    @expose
    def part(self, part_id: str = "", **kwargs: str) -> str:
        """Render the full record for a single part."""
        try:
            identifier = int(part_id)
        except ValueError:
            raise cherrypy.HTTPError(404) from None
        row = db.get_part(identifier)
        if row is None:
            raise cherrypy.HTTPError(404)
        related = db.parts_with_marking(row["code"], row["id"], row["package_id"])
        context = page_context("search", "main.part", {"part_id": identifier})
        context.update(
            part=row,
            related=related,
            package_has_image=db.has_package_image(row["package_id"]),
        )
        return render("part.html", context)

    @expose
    def package(self, *args: str, **kwargs: str) -> bytes:
        """Serve the PNG package drawing stored as a BLOB."""
        if len(args) < 2 or args[-1] != "image":
            raise cherrypy.HTTPError(404)
        code = "/".join(args[:-1])
        data = db.package_image(code)
        if data is None:
            raise cherrypy.HTTPError(404)
        cherrypy.response.headers["Content-Type"] = "image/png"
        cherrypy.response.headers["Cache-Control"] = "public, max-age=86400"
        return data

    @expose
    def about(self, **kwargs: str) -> str:
        """Render the About page."""
        return render("about.html", page_context("about", "main.about"))


def _status_code(status: str) -> int:
    """Extract the numeric status code from an HTTP status line."""
    try:
        return int(status.split(" ", 1)[0])
    except ValueError:
        return 500


def _error_context(code: int) -> dict[str, Any]:
    """Build the template context for an error page."""
    try:
        counters = db.stats()
    except (sqlite3.Error, db.DatabaseNotConfigured):
        counters = db.empty_stats()
    context = page_context("", "main.search", None, stats=counters)
    if code == 404:
        kind = "404"
    elif code >= 500:
        kind = "500"
    else:
        kind = "generic"
    context.update(
        status_code=code,
        error_title=i18n.translate(str(context["lang"]), f"error.title.{kind}"),
        error_message=i18n.translate(str(context["lang"]), f"error.message.{kind}"),
    )
    return context


def error_page(status: str, message: str, traceback: str, version: str) -> str:
    """Render every error (404, 500, ...) with the application chrome.

    Registered as ``error_page.default``. The signature is fixed by CherryPy;
    ``message``, ``traceback`` and ``version`` are accepted but not shown — the
    page shows a localized, design-consistent message instead of a traceback.
    """
    cherrypy.response.headers["Content-Type"] = "text/html;charset=utf-8"
    return render("error.html", _error_context(_status_code(status)))
