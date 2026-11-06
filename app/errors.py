"""Designed error pages for every HTTP error and unexpected failure.

The pages reuse the application chrome (``base.html``) and a localized message,
so no traceback is ever shown to the user.
"""

from __future__ import annotations

from flask import Flask
from werkzeug.exceptions import HTTPException

from . import i18n, rendering
from .rendering import page_context
from .views import shell_context


def _error_kind(code: int) -> str:
    """Map an HTTP status code to the error message keys used in ``i18n``."""
    if code == 404:
        return "404"
    if code >= 500:
        return "500"
    return "generic"


def render_error(code: int) -> str:
    """Render the designed error page for the HTTP status ``code``."""
    kind = _error_kind(code)
    lang = rendering.request_lang()
    return rendering.render(
        "error.html",
        page_context(
            "",
            **shell_context(),
            status_code=code,
            error_title=i18n.translate(lang, f"error.title.{kind}"),
            error_message=i18n.translate(lang, f"error.message.{kind}"),
        ),
    )


def handle_http_exception(error: Exception) -> tuple[str, int]:
    """Render an HTTP error (404, 405, ...) with the application chrome."""
    code = (
        error.code
        if isinstance(error, HTTPException) and error.code is not None
        else 500
    )
    return render_error(code), code


def handle_unexpected(error: Exception) -> tuple[str, int]:
    """Render an unhandled exception as a localized 500 page."""
    return render_error(500), 500


def register_error_handlers(app: Flask) -> None:
    """Register the HTTP and catch-all error handlers on ``app``."""
    app.register_error_handler(HTTPException, handle_http_exception)
    app.register_error_handler(Exception, handle_unexpected)
