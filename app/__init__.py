"""Application factory for the SMD-DB Flask web interface.

The application serves the catalogue, the part pages and the About page with
Flask and Jinja2. :func:`create_app` returns a plain :class:`flask.Flask`
application: the tests drive it through ``app.test_client()``, ``run.py`` serves
it with the multi-threaded development server and ``wsgi.py`` exposes it to
uWSGI in production.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from flask import Flask

from . import config, database, errors, rendering
from .views import PackageCodeConverter, main

#: Package directory that also holds the Jinja templates and the static assets.
APP_DIR: Path = Path(__file__).resolve().parent

#: Jinja templates and static assets.
TEMPLATES_DIR: Path = APP_DIR / "templates"
STATIC_DIR: Path = APP_DIR / "static"

#: Default SQLite catalogue (next to the package), opened read-only.
DEFAULT_DATABASE: Path = APP_DIR.parent / "smd.sqlite"

#: Development secret used to sign the session cookie when none is configured.
#: Production must set ``SMD_SECRET_KEY``.
_DEFAULT_SECRET: str = "smd-db-development-secret"


def _database_path(explicit: str | Path | None) -> Path:
    """Resolve the catalogue path: argument, then ``SMD_DATABASE``, then default."""
    if explicit is not None:
        return Path(explicit).expanduser()
    override = os.environ.get("SMD_DATABASE")
    if override:
        return Path(override).expanduser()
    return DEFAULT_DATABASE


def create_app(database_path: str | Path | None = None) -> Flask:
    """Create and configure the SMD-DB Flask application.

    Args:
        database_path: Path to the SQLite catalogue. Defaults to
            ``smd.sqlite`` next to the package (or ``SMD_DATABASE``). The file
            is opened read-only.

    Returns:
        The configured :class:`flask.Flask` application.
    """
    app = Flask(
        __name__,
        template_folder=str(TEMPLATES_DIR),
        static_folder=str(STATIC_DIR),
        static_url_path="/static",
    )
    app.config.update(
        SECRET_KEY=os.environ.get("SMD_SECRET_KEY", _DEFAULT_SECRET),
        DATABASE=str(_database_path(database_path).resolve()),
        PAGE_SIZES=config.PAGE_SIZES,
        DEFAULT_PAGE_SIZE=config.DEFAULT_PAGE_SIZE,
    )
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=config.SESSION_TIMEOUT)

    # The drawing route needs the package-code converter before the blueprint
    # is registered (Werkzeug resolves converters while parsing the rules).
    app.url_map.converters["pkg"] = PackageCodeConverter

    database.init_app(app)
    rendering.configure_environment(app)
    app.register_blueprint(main)
    errors.register_error_handlers(app)
    return app
