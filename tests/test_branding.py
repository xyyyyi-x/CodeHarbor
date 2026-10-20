"""CodeHarbor public brand and packaging contract."""

from __future__ import annotations

import importlib
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_codeharbor_branding_constants_are_centralized() -> None:
    branding = importlib.import_module("codeharbor.branding")

    assert branding.PRODUCT_NAME == "CodeHarbor"
    assert branding.PRODUCT_PACKAGE == "codeharbor"
    assert branding.PRODUCT_CLI == "codeharbor"
    assert branding.PRODUCT_TAGLINE == "Your code. Guided home."
    assert branding.PRODUCT_VERSION == "0.2.0"
    assert branding.DATA_DIR_NAME == ".codeharbor"
    assert branding.LEGACY_DATA_DIR_NAME == ".mewcode"


def test_pyproject_exposes_only_codeharbor_console_script() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["name"] == "codeharbor"
    assert project["project"]["version"] == "0.2.0"
    assert project["project"]["scripts"] == {
        "codeharbor": "codeharbor.__main__:main"
    }
    assert project["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "codeharbor"
    ]
