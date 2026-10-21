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


def test_product_facing_copy_uses_codeharbor() -> None:
    from codeharbor.prompts import build_system_prompt
    from codeharbor.plan_dialog import InlinePlanWidget, _OPTIONS

    system_prompt = build_system_prompt(work_dir=str(ROOT))
    general_agent = (
        ROOT / "codeharbor" / "agents" / "builtins" / "general-purpose.md"
    ).read_text(encoding="utf-8")
    plan_dialog = InlinePlanWidget()._build_content()
    plan_dialog += "\n".join(label for label, _choice in _OPTIONS)

    for product_copy in (system_prompt, general_agent, plan_dialog):
        assert "CodeHarbor" in product_copy
        assert "MewCode" not in product_copy


def test_readme_documents_only_current_commands_and_safe_placeholders() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "# CodeHarbor" in readme
    assert "Your code. Guided home." in readme
    assert "uv run codeharbor" in readme
    assert ".codeharbor/config.yaml" in readme
    assert "your-api-key-here" in readme
    assert "uv run mewcode" not in readme
    assert ".mewcode/config.yaml" not in readme


def test_project_instructions_use_codeharbor_filename() -> None:
    instructions = (ROOT / "CODEHARBOR.md").read_text(encoding="utf-8")

    assert instructions.startswith("# CodeHarbor 项目")
    assert not (ROOT / "MEWCODE.md").exists()
