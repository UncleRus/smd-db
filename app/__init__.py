"""Application factory for the SMD-DB CherryPy web interface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cherrypy

from . import controllers, db

#: The ``build`` directory that contains the application and the SQLite file.
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE: Path = BASE_DIR / "smd.sqlite"

#: Static assets directory (elumkit originals plus the application stylesheet).
STATIC_DIR: Path = Path(__file__).resolve().parent / "static"


def create_app(database: str | Path | None = None) -> cherrypy.Application:
    """Create and configure the SMD-DB CherryPy application.

    The returned object is a WSGI callable: tests drive it directly, while
    ``run.py`` hands it to a cheroot WSGI server.

    Args:
        database: Path to the SQLite catalogue. Defaults to ``build/smd.sqlite``.
            The file is opened read-only.

    Returns:
        The configured :class:`cherrypy.Application`.
    """
    db.configure(database or DEFAULT_DATABASE)
    config: dict[str, Any] = {
        "/": {
            "tools.sessions.on": True,
            "tools.sessions.timeout": 60 * 24,
            "error_page.default": controllers.error_page,
        },
        "/static": {
            "tools.staticdir.on": True,
            "tools.staticdir.dir": str(STATIC_DIR),
        },
    }
    return cherrypy.Application(controllers.Root(), "/", config)
