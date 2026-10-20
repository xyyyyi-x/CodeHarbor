from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

import pytest

from codeharbor.migration import (
    MigrationResult,
    migrate_legacy_data_locations,
    migrate_legacy_directory,
)


def test_missing_source_is_a_noop(tmp_path: Path) -> None:
    source = tmp_path / ".mewcode"
    target = tmp_path / ".codeharbor"

    result = migrate_legacy_directory(source, target)

    assert result == MigrationResult(source, target, "source_missing")
    assert not target.exists()


def test_migration_recursively_copies_without_mutating_source(tmp_path: Path) -> None:
    source = tmp_path / ".mewcode"
    target = tmp_path / ".codeharbor"
    nested = source / "sessions" / "default"
    nested.mkdir(parents=True)
    secret = source / "config.yaml"
    secret.write_text('api_key: "super-secret"\n', encoding="utf-8")
    transcript = nested / "session.jsonl"
    transcript.write_text('{"message":"hello"}\n', encoding="utf-8")
    timestamp = 1_700_000_000
    os.utime(secret, (timestamp, timestamp))

    before = {
        path.relative_to(source): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file()
    }
    result = migrate_legacy_directory(source, target)

    assert result == MigrationResult(source, target, "copied")
    assert (target / "config.yaml").read_bytes() == before[Path("config.yaml")]
    assert (target / "sessions/default/session.jsonl").read_bytes() == before[
        Path("sessions/default/session.jsonl")
    ]
    assert int((target / "config.yaml").stat().st_mtime) == timestamp
    assert source.exists()
    assert {
        path.relative_to(source): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file()
    } == before


def test_existing_target_takes_precedence(tmp_path: Path) -> None:
    source = tmp_path / ".mewcode"
    target = tmp_path / ".codeharbor"
    source.mkdir()
    target.mkdir()
    (source / "config.yaml").write_text("legacy", encoding="utf-8")
    current = target / "config.yaml"
    current.write_text("current", encoding="utf-8")

    result = migrate_legacy_directory(source, target)

    assert result.status == "target_exists"
    assert current.read_text(encoding="utf-8") == "current"
    assert (source / "config.yaml").read_text(encoding="utf-8") == "legacy"


def test_copy_failure_removes_only_temporary_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / ".mewcode"
    target = tmp_path / ".codeharbor"
    source.mkdir()
    (source / "keep.txt").write_text("keep", encoding="utf-8")

    def fail_after_creating_temp(src: Path, dst: Path, **kwargs: object) -> None:
        Path(dst).mkdir(parents=True)
        (Path(dst) / "partial.txt").write_text("partial", encoding="utf-8")
        raise OSError("simulated copy failure")

    monkeypatch.setattr(shutil, "copytree", fail_after_creating_temp)

    with pytest.raises(OSError, match="simulated copy failure"):
        migrate_legacy_directory(source, target)

    assert source.exists()
    assert (source / "keep.txt").read_text(encoding="utf-8") == "keep"
    assert not target.exists()
    assert not list(tmp_path.glob(".codeharbor.migration-*"))


def test_migration_logs_never_include_secret_content(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    source = tmp_path / ".mewcode"
    source.mkdir()
    api_key = "sk-test-secret-value"
    (source / "config.yaml").write_text(f"api_key: {api_key}\n", encoding="utf-8")

    with caplog.at_level(logging.INFO):
        migrate_legacy_directory(source, tmp_path / ".codeharbor")

    assert api_key not in caplog.text


def test_project_and_home_locations_migrate_independently(tmp_path: Path) -> None:
    cwd = tmp_path / "project"
    home = tmp_path / "home"
    (cwd / ".mewcode").mkdir(parents=True)
    (home / ".mewcode").mkdir(parents=True)
    (cwd / ".mewcode" / "project.txt").write_text("project", encoding="utf-8")
    (home / ".mewcode" / "user.txt").write_text("user", encoding="utf-8")

    results = migrate_legacy_data_locations(cwd, home)

    assert [result.status for result in results] == ["copied", "copied"]
    assert (cwd / ".codeharbor" / "project.txt").read_text(encoding="utf-8") == "project"
    assert (home / ".codeharbor" / "user.txt").read_text(encoding="utf-8") == "user"
