"""Read-only data access layer for the SMD catalogue.

The SQLite file shipped with the application is opened in read-only mode and is
never modified. All queries go through this module so the SQL surface stays in
one place.

Connections are cached per thread and reused: the catalogue is read-only, so a
long-lived connection per worker thread is both safe and cheaper than opening a
fresh one for every request.
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

#: Columns selected for a part row, joined with its package, manufacturer and
#: function.
PART_COLUMNS: str = (
    "p.id AS id, p.code AS code, p.name AS name, p.package_id AS package_id, "
    "pk.pins AS pins, m.name AS manufacturer, f.name AS function, "
    "p.description AS description"
)

#: Shared FROM/JOIN clause. The foreign keys are complete in the source data, so
#: inner joins do not drop any rows.
PART_FROM: str = (
    "FROM parts p "
    "JOIN manufacturers m ON m.id = p.manufacturer_id "
    "JOIN functions f ON f.id = p.function_id "
    "JOIN packages pk ON pk.code = p.package_id"
)

#: Whitelisted sort orders. Keys are the values accepted from the query string.
SORTS: dict[str, str] = {
    "marking": "p.code COLLATE NOCASE, p.name COLLATE NOCASE",
    "name": "p.name COLLATE NOCASE, p.code COLLATE NOCASE",
    "manufacturer": "m.name COLLATE NOCASE, p.name COLLATE NOCASE",
    "package": "p.package_id COLLATE NOCASE, p.name COLLATE NOCASE",
}
DEFAULT_SORT: str = "marking"

PAGE_SIZES: tuple[int, ...] = (20, 50, 100)
DEFAULT_PAGE_SIZE: int = 50


class DatabaseNotConfigured(RuntimeError):
    """Raised when the data layer is used before :func:`configure`."""


@dataclass
class SearchFilters:
    """User-supplied search conditions. Empty values mean "no filter"."""

    code: str = ""
    name: str = ""
    function_id: int | None = None
    manufacturer_id: int | None = None
    package_id: str = ""
    pins: int | None = None

    @property
    def is_empty(self) -> bool:
        """Return ``True`` when no condition is set."""
        return not any(
            (
                self.code,
                self.name,
                self.function_id,
                self.manufacturer_id,
                self.package_id,
                self.pins,
            )
        )


#: Resolved path of the catalogue; set once by :func:`configure`.
_DATABASE: Path | None = None

#: Per-thread cache of open connections keyed by database path.
_LOCAL = threading.local()

#: Catalogue size counters, computed once and reused.
_STATS_CACHE: dict[str, int] | None = None


def configure(database: str | Path) -> Path:
    """Point the data layer at ``database`` and reset cached state.

    Args:
        database: Path to the SQLite catalogue.

    Returns:
        The resolved database path.
    """
    global _DATABASE, _STATS_CACHE
    _DATABASE = Path(database).resolve()
    _STATS_CACHE = None
    for connection in _connections().values():
        connection.close()
    _LOCAL.connections = {}
    return _DATABASE


def _connections() -> dict[Path, sqlite3.Connection]:
    """Return the current thread's connection cache."""
    cache = getattr(_LOCAL, "connections", None)
    if cache is None:
        cache = {}
        _LOCAL.connections = cache
    return cast("dict[Path, sqlite3.Connection]", cache)


def get_db() -> sqlite3.Connection:
    """Return the read-only SQLite connection for the current thread.

    Raises:
        DatabaseNotConfigured: If :func:`configure` has not been called.
    """
    if _DATABASE is None:
        raise DatabaseNotConfigured("database path is not configured")
    connections = _connections()
    connection = connections.get(_DATABASE)
    if connection is None:
        uri = f"file:{_DATABASE.as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connections[_DATABASE] = connection
    return connection


def _escape_like(term: str) -> str:
    """Escape LIKE wildcards so user input is matched literally."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _build_where(filters: SearchFilters) -> tuple[str, list[Any]]:
    """Build the WHERE clause and its bound parameters for ``filters``."""
    clauses: list[str] = []
    params: list[Any] = []
    if filters.code:
        clauses.append("p.code LIKE ? ESCAPE '\\'")
        params.append(_escape_like(filters.code))
    if filters.name:
        clauses.append("p.name LIKE ? ESCAPE '\\'")
        params.append(_escape_like(filters.name))
    if filters.function_id is not None:
        clauses.append("p.function_id = ?")
        params.append(filters.function_id)
    if filters.manufacturer_id is not None:
        clauses.append("p.manufacturer_id = ?")
        params.append(filters.manufacturer_id)
    if filters.package_id:
        clauses.append("p.package_id = ?")
        params.append(filters.package_id)
    if filters.pins is not None:
        clauses.append("pk.pins = ?")
        params.append(filters.pins)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def count_parts(filters: SearchFilters) -> int:
    """Return the number of parts matching ``filters``."""
    where, params = _build_where(filters)
    row = get_db().execute(f"SELECT COUNT(*) {PART_FROM} {where}", params).fetchone()
    return int(row[0])


def fetch_parts(
    filters: SearchFilters,
    sort: str,
    limit: int,
    offset: int,
) -> list[sqlite3.Row]:
    """Return one page of parts matching ``filters``."""
    where, params = _build_where(filters)
    order = SORTS.get(sort, SORTS[DEFAULT_SORT])
    sql = (
        f"SELECT {PART_COLUMNS} {PART_FROM} {where} "
        f"ORDER BY {order} LIMIT ? OFFSET ?"
    )
    return list(get_db().execute(sql, [*params, limit, offset]).fetchall())


def get_part(part_id: int) -> sqlite3.Row | None:
    """Return a single part by id, or ``None`` when it does not exist."""
    sql = f"SELECT {PART_COLUMNS} {PART_FROM} WHERE p.id = ?"
    return cast(sqlite3.Row | None, get_db().execute(sql, (part_id,)).fetchone())


def parts_with_marking(
    code: str, exclude_id: int, package_id: str = "", limit: int = 50
) -> list[sqlite3.Row]:
    """Return other parts that share the same marking ``code``.

    The list is split into two blocks:

    1. parts in ``package_id`` (the package of the part being viewed), ordered
       by part name;
    2. all remaining parts, ordered by pin count, then package code, then name.

    The same-package block therefore stays on top, closest matches first.
    """
    sql = (
        f"SELECT {PART_COLUMNS} {PART_FROM} "
        "WHERE p.code = :code AND p.id <> :exclude_id "
        "ORDER BY "
        "CASE WHEN p.package_id = :package_id THEN 0 ELSE 1 END, "
        "CASE WHEN p.package_id = :package_id THEN p.name END COLLATE NOCASE, "
        "CASE WHEN p.package_id = :package_id THEN 0 ELSE pk.pins END, "
        "CASE WHEN p.package_id = :package_id THEN '' ELSE p.package_id END "
        "COLLATE NOCASE, "
        "p.name COLLATE NOCASE "
        "LIMIT :limit"
    )
    params: dict[str, object] = {
        "code": code,
        "exclude_id": exclude_id,
        "package_id": package_id,
        "limit": limit,
    }
    return list(get_db().execute(sql, params).fetchall())


def list_functions() -> list[sqlite3.Row]:
    """Return every function, ordered by name."""
    return list(
        get_db().execute("SELECT id, name FROM functions ORDER BY name").fetchall()
    )


def list_manufacturers() -> list[sqlite3.Row]:
    """Return every manufacturer, ordered by name."""
    return list(
        get_db().execute("SELECT id, name FROM manufacturers ORDER BY name").fetchall()
    )


def list_packages() -> list[sqlite3.Row]:
    """Return every package, ordered by code."""
    return list(
        get_db()
        .execute("SELECT code, pins FROM packages ORDER BY code COLLATE NOCASE")
        .fetchall()
    )


def package_image(code: str) -> bytes | None:
    """Return the PNG drawing for a package code, or ``None``.

    ``None`` means either the package does not exist or it has no stored
    drawing (``image IS NULL``); the caller shows a generic placeholder.
    """
    row = (
        get_db()
        .execute("SELECT image FROM packages WHERE code = ?", (code,))
        .fetchone()
    )
    if row is None or row["image"] is None:
        return None
    return bytes(row["image"])


def has_package_image(code: str) -> bool:
    """Return ``True`` when the package stores a real drawing.

    Used by the templates to decide between the drawing and the placeholder
    without pulling the BLOB into memory.
    """
    row = (
        get_db()
        .execute("SELECT image IS NOT NULL FROM packages WHERE code = ?", (code,))
        .fetchone()
    )
    return row is not None and bool(row[0])


def stats() -> dict[str, int]:
    """Return and cache the catalogue size counters."""
    global _STATS_CACHE
    if _STATS_CACHE is not None:
        return _STATS_CACHE
    connection = get_db()
    counters = {
        "parts": int(connection.execute("SELECT COUNT(*) FROM parts").fetchone()[0]),
        "markings": int(
            connection.execute("SELECT COUNT(DISTINCT code) FROM parts").fetchone()[0]
        ),
        "manufacturers": int(
            connection.execute("SELECT COUNT(*) FROM manufacturers").fetchone()[0]
        ),
        "packages": int(
            connection.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
        ),
        "functions": int(
            connection.execute("SELECT COUNT(*) FROM functions").fetchone()[0]
        ),
    }
    _STATS_CACHE = counters
    return counters


def empty_stats() -> dict[str, int]:
    """Return zeroed counters, used when the catalogue cannot be read."""
    return {
        "parts": 0,
        "markings": 0,
        "manufacturers": 0,
        "packages": 0,
        "functions": 0,
    }
