"""Entry point for the SMD-DB Flask application (development only).

The multi-threaded development server serves the application. Each request runs
in its own worker thread and gets its own SQLite connection, so concurrent
requests are served safely; the catalogue size is logged once at startup.

Production uses uWSGI behind nginx (see ``deploy/`` and ``wsgi.py``).
"""

from __future__ import annotations

import logging

from app import create_app, db

#: Interface and port the server binds to.
HOST: str = "127.0.0.1"
PORT: int = 5000


def main() -> None:
    """Run the application with Flask's built-in server."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    app = create_app()
    with app.app_context():
        stats = db.stats()
    app.logger.info(
        "catalogue ready: {parts} parts, {markings} markings, "
        "{manufacturers} manufacturers, {packages} packages, "
        "{functions} functions".format(**stats)
    )
    app.run(host=HOST, port=PORT, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
