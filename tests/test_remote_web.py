from __future__ import annotations

from types import SimpleNamespace

import pytest

from codeharbor.remote import RemoteServer
from codeharbor.web_assets import load_web_asset


@pytest.mark.parametrize(
    ("path", "content_type", "marker"),
    [
        ("/", "text/html; charset=utf-8", b"CodeHarbor"),
        ("/styles.css", "text/css; charset=utf-8", b":root"),
        ("/app.js", "text/javascript; charset=utf-8", b"WebSocket"),
        ("/assets/codeharbor-beacon.svg", "image/svg+xml", b"<svg"),
        ("/assets/favicon.svg", "image/svg+xml", b"<svg"),
        ("/vendor/marked.umd.js", "text/javascript; charset=utf-8", b"18.1.1"),
        ("/vendor/purify.min.js", "text/javascript; charset=utf-8", b"3.4.17"),
    ],
)
def test_loads_packaged_web_assets(path: str, content_type: str, marker: bytes) -> None:
    asset = load_web_asset(path)

    assert asset is not None
    assert asset.content_type == content_type
    assert marker in asset.body
    assert asset.cache_control


def test_query_string_does_not_change_asset_lookup() -> None:
    plain = load_web_asset("/styles.css")
    queried = load_web_asset("/styles.css?v=20261020")

    assert queried == plain


@pytest.mark.parametrize(
    "path",
    [
        "/missing.js",
        "/../pyproject.toml",
        "/assets/../../pyproject.toml",
        "/assets/%2e%2e/%2e%2e/pyproject.toml",
        "/assets\\..\\pyproject.toml",
        "/%2e%2e%5cpyproject.toml",
        "/codeharbor/web/index.html",
    ],
)
def test_rejects_missing_or_unsafe_asset_paths(path: str) -> None:
    assert load_web_asset(path) is None


def test_http_response_sets_security_and_content_headers() -> None:
    server = RemoteServer([])
    request = SimpleNamespace(path="/app.js?cache=1")

    response = server._process_http_request(None, request)

    assert response is not None
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/javascript; charset=utf-8"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["Cache-Control"]


def test_missing_http_asset_returns_404() -> None:
    server = RemoteServer([])

    response = server._process_http_request(None, SimpleNamespace(path="/missing.css"))

    assert response is not None
    assert response.status_code == 404
    assert response.body == b"Not Found"


def test_websocket_path_continues_upgrade() -> None:
    server = RemoteServer([])

    assert server._process_http_request(None, SimpleNamespace(path="/ws")) is None
