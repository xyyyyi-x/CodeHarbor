from __future__ import annotations

import re
from pathlib import Path

import pytest


WEB_ROOT = Path(__file__).parents[1] / "codeharbor" / "web"


def _read(name: str) -> str:
    return (WEB_ROOT / name).read_text(encoding="utf-8")


def test_frontend_uses_only_external_local_scripts() -> None:
    html = _read("index.html")

    assert "https://" not in html
    assert "http://" not in html
    assert not re.search(r"\son[a-z]+\s*=", html, re.IGNORECASE)
    assert "<script>" not in html
    assert 'src="/vendor/marked.umd.js"' in html
    assert 'src="/vendor/purify.min.js"' in html
    assert 'src="/app.js"' in html


def test_vendored_markdown_libraries_have_pinned_versions_and_licenses() -> None:
    marked = _read("vendor/marked.umd.js")
    purify = _read("vendor/purify.min.js")
    licenses = _read("vendor/LICENSES.md")

    assert "18.1.1" in marked[:500]
    assert "3.4.17" in purify[:500]
    assert "Marked 18.1.1" in licenses
    assert "DOMPurify 3.4.17" in licenses
    assert "MIT" in licenses


def test_markdown_rendering_is_marked_then_dompurify() -> None:
    script = _read("app.js")
    function = re.search(
        r"function\s+renderMarkdownSafe\s*\([^)]*\)\s*\{(?P<body>.*?)\n\s*\}",
        script,
        re.DOTALL,
    )

    assert function is not None
    body = function.group("body")
    assert "marked.parse" in body
    assert "DOMPurify.sanitize" in body
    assert body.index("marked.parse") < body.index("DOMPurify.sanitize")
    assert "ALLOWED_URI_REGEXP" in body


@pytest.mark.parametrize(
    "hostile_markdown",
    [
        '<img src=x onerror="alert(1)">',
        "[unsafe](javascript:alert(1))",
        '<svg onload="alert(1)"><script>alert(1)</script></svg>',
    ],
)
def test_security_regression_fixtures_cover_dangerous_markup(
    hostile_markdown: str,
) -> None:
    assert any(token in hostile_markdown for token in ("onerror", "javascript:", "<script>"))


def test_interactive_controls_have_accessible_names() -> None:
    html = _read("index.html")

    for control_id in (
        "new-session",
        "toggle-sessions",
        "toggle-status",
        "message-input",
        "send-message",
        "stop-response",
    ):
        tag = re.search(rf"<(?:button|textarea)[^>]*id=\"{control_id}\"[^>]*>", html)
        assert tag is not None, control_id
        assert "aria-label=" in tag.group(0), control_id


def test_frontend_contract_covers_protocol_and_helpers() -> None:
    script = _read("app.js")
    required_events = {
        "connected",
        "commands",
        "stream_text",
        "stream_end",
        "thinking_text",
        "tool_use",
        "tool_result",
        "permission_request",
        "turn_complete",
        "loop_complete",
        "usage",
        "error",
        "compact",
        "retry",
        "system",
        "command_done",
        "session_list",
        "session_active",
        "replay_user",
        "replay_assistant",
    }
    outbound_events = {
        "user_message",
        "permission_response",
        "cancel",
        "ping",
        "session_new",
        "session_resume",
    }

    for event in required_events | outbound_events:
        assert f'"{event}"' in script, event
    for helper in (
        "renderMarkdownSafe",
        "setConnectionState",
        "renderSessionList",
        "updateResponsivePanels",
    ):
        assert re.search(rf"function\s+{helper}\s*\(", script), helper


def test_responsive_and_reduced_motion_contract() -> None:
    css = _read("styles.css")

    assert "@media (max-width: 1100px)" in css
    assert "@media (max-width: 720px)" in css
    assert "prefers-reduced-motion: reduce" in css
    assert ":focus-visible" in css
