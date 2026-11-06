"""Tests for the SMD-DB Flask application.

The suite drives the app through Flask's test client (``app.test_client()``),
so sessions, cookies and error handling follow the real request path. Direct
calls into the data layer run inside ``with app.app_context()`` because
connections live on ``flask.g``.
"""

from __future__ import annotations

import hashlib
import sqlite3
import threading

import pytest
from flask import Flask, url_for
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from app import create_app, database, db, i18n

#: SHA-1 of the catalogue's former "no image" placeholder PNG. The shipped data
#: no longer contains it; this guards against it creeping back in.
PLACEHOLDER_SHA1: str = "8c573d949d77d9f03976dfa11b63de65f63dc67e"


def text(response: TestResponse) -> str:
    """Return the response body decoded as UTF-8."""
    return response.get_data(as_text=True)


@pytest.fixture()
def app() -> Flask:
    """A freshly configured application bound to the shipped catalogue."""
    return create_app()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """A test client bound to the freshly configured application."""
    return app.test_client()


# --- Search page -------------------------------------------------------------


def test_search_page_renders(client: FlaskClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert b"SMD-DB" in response.data


def test_no_search_yet_lists_nothing(client: FlaskClient) -> None:
    # Without any condition the catalogue must not be dumped on the page.
    body = text(client.get("/"))
    assert 'class="elum-table"' not in body
    assert "Start with a marking code" in body


def test_any_condition_runs_the_search(client: FlaskClient) -> None:
    body = text(client.get("/?name=LM317"))
    assert 'class="elum-table"' in body


def test_result_rows_are_links(client: FlaskClient) -> None:
    # The whole row is clickable: every row carries the part URL.
    body = text(client.get("/?code=L3"))
    assert 'class="row-link" data-href="/part/' in body


def test_part_links_keep_the_query_encoding(client: FlaskClient) -> None:
    # Reserved characters in the marking must stay percent-encoded in the
    # generated links, rather than being passed through verbatim the way
    # ``url_for`` would by default.
    body = text(client.get("/", query_string={"code": "/"}))
    assert 'data-href="/part/252?code=%2F"' in body


def test_marking_substring_is_case_insensitive(client: FlaskClient) -> None:
    upper = text(client.get("/?code=L3"))
    lower = text(client.get("/?code=l3"))
    marker = 'class="elum-toolbar-value">840<'
    assert marker in upper
    assert marker in lower


def test_marking_matches_a_substring(client: FlaskClient) -> None:
    # "L3" is a substring of 840 codes; full-code matching would
    # return only 62 rows.
    body = text(client.get("/?code=L3"))
    assert 'class="elum-toolbar-value">840<' in body
    assert 'class="elum-toolbar-value">62<' not in body


@pytest.mark.parametrize(
    ("code", "expected"),
    [("%", 14), ("*", 2433), ("+", 140), ("/", 18), ("?", 10), ("_", 98)],
)
def test_marking_special_characters_are_literal(
    client: FlaskClient, code: str, expected: int
) -> None:
    # Marking codes may contain LIKE/GLOB metacharacters. They must be matched
    # literally, never as wildcards. Counts come from the shipped catalogue.
    body = text(client.get("/", query_string={"code": code}))
    assert f'class="elum-toolbar-value">{expected:,}<' in body


def test_wildcard_does_not_match_everything(client: FlaskClient) -> None:
    # A raw LIKE pattern would have matched the whole catalogue.
    body = text(client.get("/", query_string={"code": "%"}))
    assert 'class="elum-toolbar-value">440,234<' not in body


def test_unknown_marking_shows_empty_state(client: FlaskClient) -> None:
    body = text(client.get("/?code=NO-SUCH-MARKING"))
    assert "No results" in body


def test_partial_name_filter(client: FlaskClient) -> None:
    response = client.get("/?name=LM317")
    assert response.status_code == 200
    assert "LM317" in text(response)


def test_per_page_is_validated(client: FlaskClient) -> None:
    # An unsupported page size falls back to the default (50).
    body = text(client.get("/?code=L3&per=9999"))
    assert 'value="50" selected' in body


# --- Part detail -------------------------------------------------------------


def test_known_part_renders(client: FlaskClient) -> None:
    response = client.get("/part/1")
    assert response.status_code == 200
    assert b"<img" in response.data


def test_missing_part_returns_404(client: FlaskClient) -> None:
    assert client.get("/part/999999999").status_code == 404


def test_non_numeric_part_returns_404(client: FlaskClient) -> None:
    assert client.get("/part/not-a-number").status_code == 404


def test_package_image_is_png(client: FlaskClient) -> None:
    response = client.get("/package/SOT-223/image")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG")


def test_missing_package_image_returns_404(client: FlaskClient) -> None:
    assert client.get("/package/NO-SUCH-PACKAGE/image").status_code == 404


def test_package_without_image_segment_returns_404(client: FlaskClient) -> None:
    assert client.get("/package/SOT-223").status_code == 404


def test_package_without_drawing_returns_404(client: FlaskClient) -> None:
    # SC-89-3 has image = NULL after the placeholder migration.
    assert client.get("/package/SC-89-3/image").status_code == 404


def test_package_url_encodes_reserved_characters(app: Flask) -> None:
    # The ``pkg`` converter percent-encodes every reserved character
    # (``quote(code, safe="")``).
    with app.test_request_context("/"):
        assert url_for("main.package", code="SC-70") == "/package/SC-70/image"
        assert url_for("main.package", code="SMA(W)") == "/package/SMA%28W%29/image"
        assert url_for("main.package", code="DFN-8 2x2") == "/package/DFN-8%202x2/image"


def test_part_without_package_drawing_shows_placeholder(client: FlaskClient) -> None:
    # Part 186 sits in SC-89-3, which has no stored drawing: the page must
    # render the built-in placeholder instead of a broken <img>.
    body = text(client.get("/part/186"))
    assert "elum-package-placeholder" in body
    assert "/package/SC-89-3/image" not in body


def test_part_with_package_drawing_uses_image(client: FlaskClient) -> None:
    # Part 1 sits in SC-70, which has a real drawing.
    body = text(client.get("/part/1"))
    assert "/package/SC-70/image" in body
    assert "elum-package-placeholder" not in body


def test_has_package_image_flag(app: Flask) -> None:
    with app.app_context():
        assert db.has_package_image("SOT-223") is True
        assert db.has_package_image("SC-89-3") is False
        assert db.has_package_image("NO-SUCH-PACKAGE") is False


# --- Concurrency and connection lifetime -------------------------------------


def test_database_connection_is_per_context(app: Flask) -> None:
    # Every application context opens its own connection; nothing is shared.
    connections: dict[str, sqlite3.Connection] = {}
    lock = threading.Lock()

    def worker(name: str) -> None:
        with app.app_context():
            connection = database.get_db()
            with lock:
                connections[name] = connection

    threads = [
        threading.Thread(target=worker, args=(name,)) for name in ("first", "second")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert connections["first"] is not connections["second"]


def test_connection_is_reused_within_a_context_and_closed_after(app: Flask) -> None:
    with app.app_context():
        first = database.get_db()
        assert database.get_db() is first

    with pytest.raises(sqlite3.ProgrammingError):
        first.execute("SELECT 1")


def test_concurrent_requests_are_served(app: Flask) -> None:
    # Eight threads hitting the catalogue at once: with one connection per
    # request (each created and used inside its own thread) and the default
    # SQLite thread check, every request must still succeed.
    statuses: list[int] = []
    lock = threading.Lock()

    def worker() -> None:
        response = app.test_client().get("/?code=L3")
        with lock:
            statuses.append(response.status_code)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert statuses == [200] * 8


def test_placeholder_images_are_null_and_none_remain(app: Flask) -> None:
    # The shared "no image" placeholder was replaced with NULL in the shipped
    # catalogue; no byte-identical copy may remain.
    with app.app_context():
        connection = db.get_db()
        nulls = connection.execute(
            "SELECT COUNT(*) FROM packages WHERE image IS NULL"
        ).fetchone()[0]
        assert nulls == 280
        leftover = [
            row[0]
            for row in connection.execute("SELECT code, image FROM packages")
            if row[1] is not None
            and hashlib.sha1(bytes(row[1])).hexdigest() == PLACEHOLDER_SHA1
        ]
        assert leftover == []


def test_same_marking_rest_sorted_by_pins_then_package_then_name(app: Flask) -> None:
    # Part 330770 (marking L3, package SOT-223) has no sibling in its own
    # package, so every related row belongs to the "rest" block, which is
    # ordered by pin count, then package, then name.
    with app.app_context():
        current = db.get_part(330770)
        assert current is not None
        rows = db.parts_with_marking(
            current["code"], current["id"], current["package_id"]
        )
    assert rows, "expected related parts for marking L3"
    keys = [(row["pins"], row["package_id"], row["name"]) for row in rows]
    assert keys == sorted(
        keys, key=lambda key: (key[0], key[1].casefold(), key[2].casefold())
    )


def test_same_marking_puts_current_package_first(app: Flask) -> None:
    # Part 7 (marking "%", package SC-82AB) has a sibling in the same package
    # (id 8) and parts in SC-70-5; the sibling must be listed first.
    with app.app_context():
        current = db.get_part(7)
        assert current is not None
        package = current["package_id"]
        rows = db.parts_with_marking(current["code"], current["id"], package)
    assert rows, "expected related parts for marking %"
    same_package = [row["package_id"] == package for row in rows]
    assert any(same_package), "example must have a sibling in the same package"
    # All same-package rows precede the rest.
    assert same_package == sorted(same_package, reverse=True)


# --- Localization ------------------------------------------------------------


def test_russian_labels(client: FlaskClient) -> None:
    assert "Маркировка" in text(client.get("/?lang=ru"))


def test_chinese_labels(client: FlaskClient) -> None:
    assert "丝印代码" in text(client.get("/?lang=zh"))


def test_unknown_language_falls_back_to_english(client: FlaskClient) -> None:
    assert "Marking code" in text(client.get("/?lang=xx"))


def test_translate_unknown_key_returns_key() -> None:
    assert i18n.translate("en", "no.such.key") == "no.such.key"


def test_all_languages_have_the_same_keys() -> None:
    reference = set(i18n.TRANSLATIONS["en"])
    for lang, table in i18n.TRANSLATIONS.items():
        assert reference == set(table), f"language {lang}"


def test_language_is_remembered_in_session(client: FlaskClient) -> None:
    client.get("/?lang=ru")
    # A later request without ?lang must keep the session choice.
    assert "Маркировка" in text(client.get("/"))


def test_theme_is_remembered_in_session(client: FlaskClient) -> None:
    assert 'data-theme="neon"' in text(client.get("/?theme=neon"))
    assert 'data-theme="neon"' in text(client.get("/"))


def test_explicit_choice_sets_a_persistent_session_cookie(client: FlaskClient) -> None:
    # Passing lang/theme explicitly marks the session permanent, so the cookie
    # gets an expiry (PERMANENT_SESSION_LIFETIME) instead of dying with the
    # browser session.
    response = client.get("/?lang=ru")
    cookie = response.headers.get("Set-Cookie", "")
    assert "session=" in cookie
    assert "Expires=" in cookie


def test_passive_request_does_not_set_a_session_cookie(client: FlaskClient) -> None:
    # Reading the default language/theme must not write the session cookie.
    response = client.get("/")
    assert "Set-Cookie" not in response.headers


# --- Static assets -----------------------------------------------------------


def test_static_assets_are_served_from_build(client: FlaskClient) -> None:
    response = client.get("/static/app.css")
    assert response.status_code == 200
    assert response.mimetype == "text/css"


# --- About page --------------------------------------------------------------


def test_about_renders(client: FlaskClient) -> None:
    response = client.get("/about")
    assert response.status_code == 200
    assert "440,234" in text(response)


# --- Error pages -------------------------------------------------------------


def test_missing_part_uses_designed_error_page(client: FlaskClient) -> None:
    body = text(client.get("/part/999999999"))
    assert "elum-shell" in body
    assert "Page not found" in body
    assert "Traceback" not in body


def test_unknown_route_uses_designed_error_page(client: FlaskClient) -> None:
    response = client.get("/no/such/page")
    assert response.status_code == 404
    assert "elum-shell" in text(response)
    assert "Page not found" in text(response)


def test_missing_static_file_uses_designed_error_page(client: FlaskClient) -> None:
    # A preceding session-bearing request must not leak a session into this
    # error path: rendering the error page must not touch the session, so no
    # cookie is set.
    client.get("/")
    response = client.get("/static/does-not-exist.css")
    assert response.status_code == 404
    assert "elum-shell" in text(response)
    assert "Page not found" in text(response)
    assert "Set-Cookie" not in response.headers


def test_error_page_is_localized(client: FlaskClient) -> None:
    client.get("/?lang=ru")
    body = text(client.get("/part/999999999"))
    assert "Страница не найдена" in body
    assert "К поиску" in body
