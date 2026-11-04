"""Jinja2 rendering, URL building and template context for the SMD-DB app.

The templates were written for Flask and use ``url_for``, ``merge_args``,
``part_url`` and ``search_url``. This module re-implements those helpers on top
of CherryPy so the markup can stay untouched.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode

import cherrypy
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import db, i18n

#: Directory that holds the Jinja2 templates.
TEMPLATES_DIR: Path = Path(__file__).resolve().parent / "templates"

_ENV: Environment = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(("html", "xml")),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _format_number(value: int) -> str:
    """Jinja ``num`` filter: group thousands with commas."""
    return f"{value:,}"


_ENV.filters["num"] = _format_number


def render(template: str, context: dict[str, Any]) -> str:
    """Render ``template`` with ``context`` and return the HTML text."""
    return _ENV.get_template(template).render(**context)


def query_args() -> dict[str, str]:
    """Return the request query string as a plain, first-wins mapping.

    The first occurrence of a repeated key wins, matching ``dict(request.args)``
    from the original Flask implementation.
    """
    args: dict[str, str] = {}
    for key, value in parse_qsl(cherrypy.request.query_string, keep_blank_values=True):
        args.setdefault(key, value)
    return args


def _query_string(values: dict[str, Any]) -> str:
    """Serialise ``values`` as a query string, skipping ``None`` entries."""
    clean = {key: value for key, value in values.items() if value is not None}
    if not clean:
        return ""
    return "?" + urlencode(clean)


def url_for(endpoint: str, **values: Any) -> str:
    """Build a URL for ``endpoint``, translating Flask endpoint names.

    Supported endpoints: ``static``, ``main.search``, ``main.part``,
    ``main.package_image`` and ``main.about``. Extra keyword arguments become
    query-string parameters.

    Raises:
        ValueError: If the endpoint is unknown.
    """
    if endpoint == "static":
        filename = str(values.pop("filename", ""))
        return "/static/" + quote(filename, safe="/") + _query_string(values)
    if endpoint == "main.package_image":
        code = str(values.pop("code", ""))
        return "/package/" + quote(code, safe="") + "/image" + _query_string(values)
    if endpoint == "main.part":
        part_id = values.pop("part_id", "")
        return f"/part/{quote(str(part_id), safe='')}" + _query_string(values)
    if endpoint == "main.search":
        return "/" + _query_string(values)
    if endpoint == "main.about":
        return "/about" + _query_string(values)
    raise ValueError(f"unknown endpoint: {endpoint!r}")


def current_lang() -> str:
    """Resolve the active language from the request or the session."""
    lang = query_args().get("lang") or cherrypy.session.get("lang") or i18n.DEFAULT_LANG
    if lang not in i18n.TRANSLATIONS:
        lang = i18n.DEFAULT_LANG
    cherrypy.session["lang"] = lang
    return lang


def current_theme() -> str:
    """Resolve the active theme from the request or the session."""
    theme = (
        query_args().get("theme") or cherrypy.session.get("theme") or i18n.DEFAULT_THEME
    )
    if theme not in i18n.THEMES:
        theme = i18n.DEFAULT_THEME
    cherrypy.session["theme"] = theme
    return theme


def _apply_overrides(args: dict[str, Any], overrides: dict[str, object]) -> None:
    """Merge ``overrides`` into ``args``; ``None`` removes a key."""
    for key, value in overrides.items():
        if value is None:
            args.pop(key, None)
        else:
            args[key] = value


def page_context(
    active: str,
    endpoint: str,
    view_args: dict[str, Any] | None = None,
    *,
    stats: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build the globals shared by every template.

    Args:
        active: Navigation item to mark as current (``search`` or ``about``).
        endpoint: Logical endpoint of the current page, used by ``merge_args``.
        view_args: Path arguments of the current page (for example ``part_id``).
        stats: Catalogue counters; read from the database when omitted.

    Returns:
        The template context dictionary.
    """
    lang = current_lang()
    theme = current_theme()
    path_args: dict[str, Any] = dict(view_args or {})

    def translate(key: str, **kwargs: object) -> str:
        return i18n.translate(lang, key, **kwargs)

    def search_url(**overrides: object) -> str:
        """Build a search URL from the current query, applying overrides."""
        args: dict[str, Any] = dict(query_args())
        _apply_overrides(args, overrides)
        return url_for("main.search", **args)

    def part_url(part_id: int) -> str:
        """Build a part URL that carries the current search query back with it."""
        args: dict[str, Any] = dict(query_args())
        args["part_id"] = part_id
        return url_for("main.part", **args)

    def merge_args(**overrides: object) -> str:
        """Build a URL for the current endpoint with merged query arguments."""
        args: dict[str, Any] = dict(path_args)
        args.update(query_args())
        _apply_overrides(args, overrides)
        return url_for(endpoint, **args)

    return {
        "t": translate,
        "lang": lang,
        "theme": theme,
        "languages": i18n.LANGUAGES,
        "themes": i18n.THEMES,
        "page_sizes": db.PAGE_SIZES,
        "url_for": url_for,
        "search_url": search_url,
        "part_url": part_url,
        "merge_args": merge_args,
        "stats": stats if stats is not None else db.stats(),
        "active": active,
    }
