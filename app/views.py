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
        "home_link": url_for("main.index"),
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
    """URL of the single package-image endpoint for a package code.

    The endpoint serves the stored drawing, or its placeholder when the
    package has none, so the same URL works for every package.
    """
    return url_for("main.package", code=code)


def _package_images(rows: Iterable[sqlite3.Row]) -> dict[str, str]:
    """Package-image URLs for the package codes appearing in ``rows``.

    ``rows`` may repeat a package; the mapping is keyed by code so the template
    can look the URL up for each row.
    """
    codes = {str(row["package_id"]) for row in rows}
    return {code: _package_image_url(code) for code in codes}


def _image_mimetype(data: bytes) -> str:
    """Guess an image's MIME type from its leading bytes.

    The catalogue stores PNG today; the other signatures are recognised so the
    endpoint keeps working if a drawing is ever stored in another format.
    """
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"BM"):
        return "image/bmp"
    stripped = data.lstrip()
    if stripped.startswith((b"<svg", b"<?xml")):
        return "image/svg+xml"
    return "application/octet-stream"


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
            package_images=_package_images(result.rows),
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
            package_images=_package_images(related),
            package_image_url=_package_image_url(str(row["package_id"])),
        ),
    )


@main.get("/package/<pkg:code>/image")
def package(code: str) -> Response:
    """Serve the drawing for a package code, or its placeholder.

    One endpoint for every package: the stored drawing (in whatever format it
    is kept) when there is one, and the shared placeholder drawing otherwise.
    Both the part page and the list tooltips point at this URL, so there is no
    "has a drawing" branch anywhere and no request ever misses.

    The package code may contain slashes and reserved characters; the
    ``pkg`` converter matches the code and percent-encodes it in generated URLs.
    """
    cache = {"Cache-Control": "public, max-age=86400"}
    data = _catalogue.image(code)
    if data is None:
        return Response(
            rendering.render("_package_placeholder.svg", {}),
            mimetype="image/svg+xml",
            headers=cache,
        )
    return Response(data, mimetype=_image_mimetype(data), headers=cache)


@main.get("/about")
def about() -> str:
    """Render the About page."""
    return rendering.render("about.html", page_context("about", **shell_context()))
