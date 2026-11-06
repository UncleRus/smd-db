"""WSGI entry point for production servers (uWSGI on rpi41).

uWSGI loads the application as ``wsgi:application`` (see ``deploy/uwsgi.ini``).
The development server lives in ``run.py`` and is not used in production.
"""

from __future__ import annotations

from app import create_app

#: WSGI callable imported by uWSGI.
application = create_app()
