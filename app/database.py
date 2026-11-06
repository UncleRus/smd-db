"""Database access for the SMD-DB Flask application.

The catalogue is a read-only SQLite file. SQLite connections are confined to
the thread that created them, so this application never leans on the driver's
thread tolerance (``check_same_thread``): instead one connection is opened per
request (or per application context) and stored on :data:`flask.g`, then closed
when the context ends by the ``teardown_appcontext`` hook.

Because every connection is created and used inside a single thread, the
default SQLite thread check stays in force and nothing is shared across
worker threads. The multi-threaded development server (``threaded=True``) can
therefore serve concurrent requests safely.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, current_app, g

__all__ = [
    "DatabaseNotConfigured",
    "close_db",
    "connect",
    "database_path",
    "get_db",
    "init_app",
]


class DatabaseNotConfigured(RuntimeError):
    """Raised when the data layer is used before a database is installed."""


def connect(database: str | Path) -> sqlite3.Connection:
    """Open a read-only SQLite connection to ``database``."""
    uri = f"file:{Path(database).resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def database_path() -> Path:
    """Return the resolved path of the configured catalogue file."""
    return Path(current_app.config["DATABASE"]).resolve()


def get_db() -> sqlite3.Connection:
    """Return the connection bound to the current application context.

    The connection is opened lazily on first use and cached on
    :data:`flask.g`, so every query in one request shares a single handle that
    belongs to the thread running that request.
    """
    if "db" not in g:
        g.db = connect(database_path())
    return g.db  # type: ignore[no-any-return]


def close_db(exc: BaseException | None = None) -> None:
    """Close the context's connection, if one was opened."""
    connection: sqlite3.Connection | None = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_app(app: Flask) -> None:
    """Register the per-context connection teardown with ``app``."""
    app.teardown_appcontext(close_db)
