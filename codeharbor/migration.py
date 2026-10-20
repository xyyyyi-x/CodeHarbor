# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com

from __future__ import annotations

import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from codeharbor.branding import DATA_DIR_NAME, LEGACY_DATA_DIR_NAME

logger = logging.getLogger(__name__)

MigrationStatus = Literal["copied", "target_exists", "source_missing"]


@dataclass(frozen=True, slots=True)
class MigrationResult:
    source: Path
    target: Path
    status: MigrationStatus


def migrate_legacy_directory(source: Path, target: Path) -> MigrationResult:
    """Copy a legacy data directory without deleting or overwriting user data."""
    source = Path(source)
    target = Path(target)
    if target.exists():
        return MigrationResult(source, target, "target_exists")
    if not source.exists():
        return MigrationResult(source, target, "source_missing")

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.migration-{uuid.uuid4().hex}")
    try:
        shutil.copytree(source, temporary, copy_function=shutil.copy2)
        if target.exists():
            shutil.rmtree(temporary)
            return MigrationResult(source, target, "target_exists")
        temporary.rename(target)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise

    logger.info("Migrated legacy CodeHarbor data directory from %s to %s", source, target)
    return MigrationResult(source, target, "copied")


def migrate_legacy_data_locations(cwd: Path, home: Path) -> list[MigrationResult]:
    """Migrate project and user data locations independently."""
    locations = (Path(cwd), Path(home))
    return [
        migrate_legacy_directory(
            location / LEGACY_DATA_DIR_NAME,
            location / DATA_DIR_NAME,
        )
        for location in locations
    ]
