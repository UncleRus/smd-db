"""Application configuration for the SMD-DB Flask web interface.

The values are plain module constants; :func:`smd.create_app` copies them
into the Flask configuration so request handlers can read them through
``current_app.config``.
"""

from __future__ import annotations

#: Server-side session lifetime, in minutes. Flask stores the session in a
#: signed cookie, so this is the signed-cookie lifetime.
SESSION_TIMEOUT: int = 60 * 24

#: Selectable page sizes for the search results.
PAGE_SIZES: tuple[int, ...] = (20, 50, 100)

#: Page size used when none (or an invalid one) is requested.
DEFAULT_PAGE_SIZE: int = 50
