"""Tests for the SMD-DB CherryPy application.

The application is a plain WSGI callable, so the suite drives it directly with
a small client built on ``wsgiref`` -- no live server and no Flask/Werkzeug.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults

import pytest

from app import create_app, db, i18n

#: Reference copy of the "no image" placeholder used by the data migration.
PLACEHOLDER_PNG: Path = (
    Path(__file__).resolve().parent.parent / "migrations" / "empty.png"
)

StartResponse = Callable[[str, list[tuple[str, str]], Any], None]
WSGIApp = Callable[[dict[str, Any], StartResponse], Iterable[bytes]]


class Response:
    """A captured WSGI response."""

    def __init__(
        self, status: str, headers: list[tuple[str, str]], body: bytes
    ) -> None:
        self.status = status
        self.headers = headers
        self.body = body

    @property
    def status_code(self) -> int:
        """The numeric HTTP status code."""
        return int(self.status.split(" ", 1)[0])

    @property
    def text(self) -> str:
        """The response body decoded as UTF-8."""
        return self.body.decode("utf-8")

    @property
    def mimetype(self) -> str:
        """The media type from the Content-Type header, without parameters."""
        return self.header("Content-Type").split(";", 1)[0].strip()

    def header(self, name: str, default: str = "") -> str:
        """Return the first header matching ``name`` (case-insensitive)."""
        for key, value in self.headers:
            if key.lower() == name.lower():
                return value
        return default


class Client:
    """Minimal WSGI test client that keeps session cookies between requests."""

    def __init__(self, app: WSGIApp) -> None:
        self._app = app
        self._cookies: dict[str, str] = {}

    def get(self, path: str, query_string: dict[str, object] | None = None) -> Response:
        """Perform a GET request and return the captured response."""
        if "?" in path:
            path, _, embedded = path.partition("?")
        else:
            embedded = ""
        if query_string is not None:
            embedded = urlencode(query_string)

        environ: dict[str, Any] = {}
        setup_testing_defaults(environ)
        environ["REQUEST_METHOD"] = "GET"
        environ["PATH_INFO"] = path
        environ["QUERY_STRING"] = embedded
        if self._cookies:
            environ["HTTP_COOKIE"] = "; ".join(
                f"{name}={value}" for name, value in self._cookies.items()
            )

        captured: dict[str, Any] = {}

        def start_response(
            status: str,
            headers: list[tuple[str, str]],
            exc_info: Any = None,
        ) -> None:
            captured["status"] = status
            captured["headers"] = headers

        body = b"".join(self._app(environ, start_response))
        headers = list(captured["headers"])
        self._store_cookies(headers)
        return Response(str(captured["status"]), headers, body)

    def _store_cookies(self, headers: list[tuple[str, str]]) -> None:
        """Remember any cookies the server set."""
        for key, value in headers:
            if key.lower() != "set-cookie":
                continue
            cookie = SimpleCookie()
            cookie.load(value)
            for name, morsel in cookie.items():
                self._cookies[name] = morsel.value


@pytest.fixture()
def client() -> Client:
    """A test client bound to a freshly configured application."""
    return Client(create_app())


# --- Search page -------------------------------------------------------------


def test_search_page_renders(client: Client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert b"SMD-DB" in response.body


def test_no_search_yet_lists_nothing(client: Client) -> None:
    # Without any condition the catalogue must not be dumped on the page.
    text = client.get("/").text
    assert 'class="elum-table"' not in text
    assert "Start with a marking code" in text


def test_any_condition_runs_the_search(client: Client) -> None:
    text = client.get("/?name=LM317").text
    assert 'class="elum-table"' in text


def test_result_rows_are_links(client: Client) -> None:
    # The whole row is clickable: every row carries the part URL.
    text = client.get("/?code=L3").text
    assert 'class="row-link" data-href="/part/' in text


def test_marking_substring_is_case_insensitive(client: Client) -> None:
    upper = client.get("/?code=L3").text
    lower = client.get("/?code=l3").text
    marker = 'class="elum-toolbar-value">840<'
    assert marker in upper
    assert marker in lower


def test_marking_matches_a_substring(client: Client) -> None:
    # "L3" is a substring of 840 codes; full-code matching would
    # return only 62 rows.
    text = client.get("/?code=L3").text
    assert 'class="elum-toolbar-value">840<' in text
    assert 'class="elum-toolbar-value">62<' not in text


@pytest.mark.parametrize(
    ("code", "expected"),
    [("%", 14), ("*", 2433), ("+", 140), ("/", 18), ("?", 10), ("_", 98)],
)
def test_marking_special_characters_are_literal(
    client: Client, code: str, expected: int
) -> None:
    # Marking codes may contain LIKE/GLOB metacharacters. They must be matched
    # literally, never as wildcards. Counts come from the shipped catalogue.
    text = client.get("/", query_string={"code": code}).text
    assert f'class="elum-toolbar-value">{expected:,}<' in text


def test_wildcard_does_not_match_everything(client: Client) -> None:
    # A raw LIKE pattern would have matched the whole catalogue.
    text = client.get("/", query_string={"code": "%"}).text
    assert 'class="elum-toolbar-value">440,234<' not in text


def test_unknown_marking_shows_empty_state(client: Client) -> None:
    text = client.get("/?code=NO-SUCH-MARKING").text
    assert "No results" in text


def test_partial_name_filter(client: Client) -> None:
    response = client.get("/?name=LM317")
    assert response.status_code == 200
    assert "LM317" in response.text


def test_per_page_is_validated(client: Client) -> None:
    # An unsupported page size falls back to the default (50).
    text = client.get("/?code=L3&per=9999").text
    assert 'value="50" selected' in text


# --- Part detail -------------------------------------------------------------


def test_known_part_renders(client: Client) -> None:
    response = client.get("/part/1")
    assert response.status_code == 200
    assert b"<img" in response.body


def test_missing_part_returns_404(client: Client) -> None:
    assert client.get("/part/999999999").status_code == 404


def test_non_numeric_part_returns_404(client: Client) -> None:
    assert client.get("/part/not-a-number").status_code == 404


def test_package_image_is_png(client: Client) -> None:
    response = client.get("/package/SOT-223/image")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.body.startswith(b"\x89PNG")


def test_missing_package_image_returns_404(client: Client) -> None:
    assert client.get("/package/NO-SUCH-PACKAGE/image").status_code == 404


def test_package_without_image_segment_returns_404(client: Client) -> None:
    assert client.get("/package/SOT-223").status_code == 404


def test_package_without_drawing_returns_404(client: Client) -> None:
    # SC-89-3 has image = NULL after the placeholder migration.
    assert client.get("/package/SC-89-3/image").status_code == 404


def test_part_without_package_drawing_shows_placeholder(client: Client) -> None:
    # Part 186 sits in SC-89-3, which has no stored drawing: the page must
    # render the built-in placeholder instead of a broken <img>.
    text = client.get("/part/186").text
    assert "elum-package-placeholder" in text
    assert "/package/SC-89-3/image" not in text


def test_part_with_package_drawing_uses_image(client: Client) -> None:
    # Part 1 sits in SC-70, which has a real drawing.
    text = client.get("/part/1").text
    assert "/package/SC-70/image" in text
    assert "elum-package-placeholder" not in text


def test_has_package_image_flag() -> None:
    create_app()  # configures the data layer
    assert db.has_package_image("SOT-223") is True
    assert db.has_package_image("SC-89-3") is False
    assert db.has_package_image("NO-SUCH-PACKAGE") is False


def test_placeholder_images_are_null_and_none_remain() -> None:
    # The shared "no image" placeholder was replaced with NULL by
    # migrations/0001_null_placeholder_images.py.
    create_app()  # configures the data layer
    connection = db.get_db()
    nulls = connection.execute(
        "SELECT COUNT(*) FROM packages WHERE image IS NULL"
    ).fetchone()[0]
    assert nulls == 280
    # No byte-identical copy of the reference placeholder may remain.
    digest = hashlib.sha1(PLACEHOLDER_PNG.read_bytes()).hexdigest()
    leftover = [
        row[0]
        for row in connection.execute("SELECT code, image FROM packages")
        if row[1] is not None and hashlib.sha1(bytes(row[1])).hexdigest() == digest
    ]
    assert leftover == []


def test_same_marking_rest_sorted_by_pins_then_package_then_name() -> None:
    # Part 330770 (marking L3, package SOT-223) has no sibling in its own
    # package, so every related row belongs to the "rest" block, which is
    # ordered by pin count, then package, then name.
    create_app()  # configures the data layer
    current = db.get_part(330770)
    assert current is not None
    rows = db.parts_with_marking(current["code"], current["id"], current["package_id"])
    assert rows, "expected related parts for marking L3"
    keys = [(row["pins"], row["package_id"], row["name"]) for row in rows]
    assert keys == sorted(
        keys, key=lambda key: (key[0], key[1].casefold(), key[2].casefold())
    )


def test_same_marking_puts_current_package_first() -> None:
    # Part 7 (marking "%", package SC-82AB) has a sibling in the same package
    # (id 8) and parts in SC-70-5; the sibling must be listed first.
    create_app()  # configures the data layer
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


def test_russian_labels(client: Client) -> None:
    assert "Маркировка" in client.get("/?lang=ru").text


def test_chinese_labels(client: Client) -> None:
    assert "丝印代码" in client.get("/?lang=zh").text


def test_unknown_language_falls_back_to_english(client: Client) -> None:
    assert "Marking code" in client.get("/?lang=xx").text


def test_translate_unknown_key_returns_key() -> None:
    assert i18n.translate("en", "no.such.key") == "no.such.key"


def test_all_languages_have_the_same_keys() -> None:
    reference = set(i18n.TRANSLATIONS["en"])
    for lang, table in i18n.TRANSLATIONS.items():
        assert reference == set(table), f"language {lang}"


def test_language_is_remembered_in_session(client: Client) -> None:
    client.get("/?lang=ru")
    # A later request without ?lang must keep the session choice.
    assert "Маркировка" in client.get("/").text


def test_theme_is_remembered_in_session(client: Client) -> None:
    assert 'data-theme="neon"' in client.get("/?theme=neon").text
    assert 'data-theme="neon"' in client.get("/").text


# --- About page --------------------------------------------------------------


def test_about_renders(client: Client) -> None:
    response = client.get("/about")
    assert response.status_code == 200
    assert "440,234" in response.text


# --- Error pages (overriding CherryPy defaults) ------------------------------


def test_missing_part_uses_designed_error_page(client: Client) -> None:
    text = client.get("/part/999999999").text
    assert "elum-shell" in text
    assert "Page not found" in text
    assert "Powered by CherryPy" not in text


def test_unknown_route_uses_designed_error_page(client: Client) -> None:
    response = client.get("/no/such/page")
    assert response.status_code == 404
    assert "elum-shell" in response.text
    assert "Page not found" in response.text


def test_missing_static_file_uses_designed_error_page(client: Client) -> None:
    response = client.get("/static/does-not-exist.css")
    assert response.status_code == 404
    assert "elum-shell" in response.text
    assert "Page not found" in response.text


def test_error_page_is_localized(client: Client) -> None:
    client.get("/?lang=ru")
    text = client.get("/part/999999999").text
    assert "Страница не найдена" in text
    assert "К поиску" in text
