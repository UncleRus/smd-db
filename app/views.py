"""Flask views for SMD-DB.

The views are deliberately thin: they read the request, ask the
:class:`~app.services.Catalogue` for data, build the page URLs and hand the
context to Jinja. Paths come from Flask's :func:`~flask.url_for` (routes by
endpoint name, no hard-coded paths); the query string is appended separately so
the links stay correctly and predictably encoded. No template builds a URL:
every link arrives in the context as a finished string.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import quote, urlencode

from flask import Blueprint, Response, abort, request, url_for
from werkzeug.routing import BaseConverter

from . import i18n, rendering
from .rendering import page_context, query_args
from .services import Catalogue, SearchResult

main = Blueprint("main", __name__)

#: Static asset URLs, served by Flask's ``/static`` route.
INDEX_CSS: str = "/static/elumkit/index.css"
APP_CSS: str = "/static/app.css"
APP_JS: str = "/static/app.js"

#: Read-only catalogue service shared by every request (it holds no state).
_catalogue = Catalogue()


class PackageCodeConverter(BaseConverter):
    """URL Converter for package codes on the drawing route.

    Package codes may contain slashes and reserved characters. The incoming
    path accepts slashes (``[^/].*?``, non-greedy so it stops before the literal
    ``/image`` segment), while the generated URL percent-encodes every character
    outside the unreserved set with ``quote(code, safe="")``.
    """

    regex = r"[^/].*?"
    part_isolating = False

    def to_url(self, value: Any) -> str:
        return quote(str(value), safe="")


# --- URL building ------------------------------------------------------------


def _url(path: str, params: Mapping[str, Any]) -> str:
    """Return ``path`` with the non-empty ``params`` encoded as a query string.

    The query is encoded here rather than through ``url_for``'s extra keywords:
    Werkzeug leaves some reserved characters (``/``, ``?``, ``*``, parens…)
    unescaped in query values, so this keeps the links fully and predictably
    percent-encoded.
    """
    clean = {key: value for key, value in params.items() if value not in (None, "")}
    if not clean:
        return path
    return f"{path}?{urlencode(clean)}"


def _route(endpoint: str, params: Mapping[str, Any], **values: Any) -> str:
    """Return the ``url_for`` path for ``endpoint`` plus the ``params`` query."""
    return _url(url_for(endpoint, **values), params)


def shell_context() -> dict[str, Any]:
    """URLs and assets the shared page shell (``base.html``) needs.

    The language switch keeps the current page and query and only swaps the
    language, so switching languages never drops the search.
    """
    query = dict(query_args())
    lang = rendering.request_lang()
    theme = rendering.request_theme()
    path = request.path
    return {
        "index_css": INDEX_CSS,
        "app_css": APP_CSS,
        "app_js": APP_JS,
        "search_action": url_for("main.index"),
        "search_link": _route("main.index", {"lang": lang, "theme": theme}),
        "results_link": _route("main.index", query),
        "about_link": _route("main.about", {"lang": lang, "theme": theme}),
        "lang_links": {
            code: _url(path, {**query, "lang": code}) for code, _label in i18n.LANGUAGES
        },
    }


def _part_links(rows: Iterable[sqlite3.Row]) -> dict[int, str]:
    """Part URLs for the given rows, carrying the current search query."""
    query = dict(query_args())
    return {
        int(row["id"]): _route("main.part", query, part_id=row["id"]) for row in rows
    }


def _page_links(result: SearchResult) -> dict[str, Any]:
    """Pagination URLs for a search result: page links plus prev/next."""
    query = dict(query_args())

    def page_url(number: int) -> str:
        return _route("main.index", {**query, "page": number})

    links = {
        number: page_url(number) for number in result.page_items if number is not None
    }
    return {
        "page_links": links,
        "prev_link": page_url(result.page - 1) if result.page > 1 else None,
        "next_link": page_url(result.page + 1) if result.page < result.pages else None,
    }


def _package_image_url(code: str) -> str:
    """URL of the PNG drawing for a package code."""
    return url_for("main.package", code=code)


# --- Routes ------------------------------------------------------------------


@main.get("/")
def index() -> str:
    """Render the search form and one page of results."""
    result = _catalogue.search(query_args())
    functions, manufacturers, packages = _catalogue.menu()
    return rendering.render(
        "search.html",
        page_context(
            "search",
            **shell_context(),
            **_page_links(result),
            part_links=_part_links(result.rows),
            filters=result.filters,
            searched=result.searched,
            rows=result.rows,
            total=result.total,
            page=result.page,
            pages=result.pages,
            page_items=result.page_items,
            per=result.per,
            sort=result.sort,
            functions=functions,
            manufacturers=manufacturers,
            packages=packages,
        ),
    )


@main.get("/part/<part_id>")
def part(part_id: str) -> str:
    """Render the full record for a single part."""
    try:
        identifier = int(part_id)
    except ValueError:
        abort(404)
    row = _catalogue.part(identifier)
    if row is None:
        abort(404)
    related = _catalogue.related(row)
    return rendering.render(
        "part.html",
        page_context(
            "search",
            **shell_context(),
            part=row,
            related=related,
            part_links=_part_links(related),
            package_has_image=_catalogue.has_image(row["package_id"]),
            package_image_url=_package_image_url(str(row["package_id"])),
        ),
    )


@main.get("/package/<pkg:code>/image")
def package(code: str) -> Response:
    """Serve the PNG package drawing stored as a BLOB.

    The package code may contain slashes and reserved characters; the
    ``pkg`` converter matches the code and percent-encodes it in generated URLs.
    """
    data = _catalogue.image(code)
    if data is None:
        abort(404)
    return Response(
        data,
        mimetype="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@main.get("/about")
def about() -> str:
    """Render the About page."""
    return rendering.render("about.html", page_context("about", **shell_context()))
