from __future__ import annotations

import argparse
import logging
import sys
from types import SimpleNamespace

import pytest

from codeharbor import __main__ as cli
from codeharbor.remote import RemoteServer, is_loopback_host


def test_parser_uses_codeharbor_identity_and_secure_remote_defaults() -> None:
    parser = cli.build_parser()

    assert parser.prog == "codeharbor"
    args = parser.parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 18888


def test_parser_accepts_explicit_remote_host_and_port() -> None:
    args = cli.build_parser().parse_args(
        ["--remote", "--host", "0.0.0.0", "--port", "2048"]
    )

    assert args.remote is True
    assert args.host == "0.0.0.0"
    assert args.port == 2048


@pytest.mark.parametrize("value", ["0", "65536", "-1", "not-a-number"])
def test_parse_port_rejects_invalid_values(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        cli.parse_port(value)


@pytest.mark.parametrize("value", ["1", "18888", "65535"])
def test_parse_port_accepts_valid_values(value: str) -> None:
    assert cli.parse_port(value) == int(value)


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("localhost", True),
        ("LOCALHOST", True),
        ("127.0.0.1", True),
        ("127.255.255.254", True),
        ("::1", True),
        ("0.0.0.0", False),
        ("192.168.1.10", False),
        ("example.com", False),
    ],
)
def test_loopback_host_recognition(host: str, expected: bool) -> None:
    assert is_loopback_host(host) is expected


def test_main_passes_remote_bind_options(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeRemoteServer:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        async def run(self) -> None:
            return None

    config = SimpleNamespace(
        permission_mode="default",
        raw_hooks=[],
        providers=[],
        mcp_servers=[],
    )
    monkeypatch.setattr(cli, "migrate_legacy_data_locations", lambda *args: [])
    monkeypatch.setattr(cli, "load_config", lambda: config)
    monkeypatch.setattr(cli, "load_hooks", lambda raw: [])
    monkeypatch.setattr("codeharbor.remote.RemoteServer", FakeRemoteServer)
    monkeypatch.setattr(
        sys,
        "argv",
        ["codeharbor", "--remote", "--host", "0.0.0.0", "--port", "24444"],
    )

    cli.main()

    assert captured["addr"] == "0.0.0.0"
    assert captured["port"] == 24444


def test_non_loopback_bind_warns_exactly_once_without_config_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "sk-should-never-appear"

    with caplog.at_level(logging.WARNING):
        server = RemoteServer([], addr="0.0.0.0", config={"api_key": secret})

    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert server.addr == "0.0.0.0"
    assert len(warnings) == 1
    assert "unauthenticated" in warnings[0].getMessage().lower()
    assert secret not in caplog.text
