"""Development entry point for the SMD-DB web application.

Run with::

    build/.venv/bin/python build/run.py

then open http://127.0.0.1:5000/ .
"""

from __future__ import annotations

from cheroot import wsgi

from app import create_app

#: Interface and port the development server binds to.
HOST: str = "127.0.0.1"
PORT: int = 5000


def main() -> None:
    """Serve the CherryPy application with the bundled cheroot WSGI server."""
    application = create_app()
    server = wsgi.Server((HOST, PORT), application)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
