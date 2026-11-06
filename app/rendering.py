"""Jinja2 integration and template context for the SMD-DB Flask application.

Rendering uses Flask's Jinja environment, configured by
:func:`configure_environment`: the ``num`` filter, a ``finalize`` hook that
renders ``None`` as an empty string, and ``t`` (translation) are installed once
per application.

The controller builds the page URLs and hands them over in the context; the
only request-aware helper here is ``t``, which reads the current request itself.
"""

from __future__ import annotations

from collections.abc import Container
from typing import Any, cast

from flask import Flask, current_app, g, request, session

from . import config, db, i18n

# --- Request state: query parameters, language and theme ---------------------


def query_args() -> dict[str, str]:
    """Return the query-string parameters parsed for this request."""
    return dict(request.args)


def _pick(value: str | None, allowed: Container[str], default: str) -> str:
    """Return ``value`` when it is one of ``allowed``, otherwise ``default``."""
    if value is not None and value in allowed:
        return value
    return default


def _resolve(key: str, allowed: Container[str], default: str) -> str:
    """Resolve a per-request choice and cache it on the request.

    The query parameter wins over the session value, which wins over the
    default. The result is cached on :data:`flask.g` so the template context
    and the error page agree on a single value per request. The session is only
    written when the parameter was passed explicitly. The choice is remembered
    beyond the browser session (``session.permanent``), so from then on every
    response refreshes the cookie.
    """
    cached = getattr(g, key, None)
    if cached is not None:
        return cast(str, cached)
    raw = request.args.get(key)
    explicit = raw is not None
    if raw is None:
        raw = session.get(key)
    value = _pick(raw, allowed, default)
    setattr(g, key, value)
    if explicit:
        session[key] = value
        # Persist the choice beyond the browser session: the cookie then carries
        # an expiry of ``PERMANENT_SESSION_LIFETIME`` (see create_app).
        session.permanent = True
    return value


def request_lang() -> str:
    """Active language: query parameter, then session, then the default."""
    return _resolve("lang", i18n.TRANSLATIONS, i18n.DEFAULT_LANG)


def request_theme() -> str:
    """Active theme: query parameter, then session, then the default."""
    return _resolve("theme", i18n.THEMES, i18n.DEFAULT_THEME)


# --- Translation and shared context ------------------------------------------


def t(key: str, **kwargs: object) -> str:
    """Translate ``key`` into the active language."""
    return i18n.translate(request_lang(), key, **kwargs)


def _shared_context() -> dict[str, Any]:
    """Values every page needs, resolved once per request."""
    return {
        "lang": request_lang(),
        "theme": request_theme(),
        "languages": i18n.LANGUAGES,
        "themes": i18n.THEMES,
        "page_sizes": config.PAGE_SIZES,
        "stats": db.stats(),
    }


def page_context(active: str, **data: Any) -> dict[str, Any]:
    """Build the render context for a controller response.

    ``data`` carries everything the controller wants to hand the template,
    including the URLs it built for the page.
    """
    return {**_shared_context(), **data, "active": active}


def render(template: str, context: dict[str, Any]) -> str:
    """Render ``template`` with ``context`` through the application environment."""
    return current_app.jinja_env.get_template(template).render(**context)


# --- Filters and environment -------------------------------------------------


def _format_number(value: int) -> str:
    """Jinja ``num`` filter: group thousands with commas."""
    return f"{value:,}"


def _finalize(value: object) -> object:
    """Render ``None`` as an empty string."""
    return "" if value is None else value


def configure_environment(app: Flask) -> None:
    """Install the application's Jinja filters, globals and finalizer on ``app``."""
    app.jinja_env.filters["num"] = _format_number
    app.jinja_env.finalize = _finalize
    # ``t`` is stateless (it reads the request itself), so it is a plain
    # environment global rather than a per-request value.
    app.jinja_env.globals["t"] = t
