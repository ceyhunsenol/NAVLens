"""Distribution metadata contract for release artifacts."""

import tomllib
from importlib.metadata import requires, version
from pathlib import Path

import navlens


def test_public_version_matches_installed_distribution() -> None:
    cargo_manifest = Path(__file__).parents[2] / "Cargo.toml"
    workspace_version = tomllib.loads(cargo_manifest.read_text(encoding="utf-8"))["workspace"][
        "package"
    ]["version"]

    assert navlens.__version__ == version("navlens")
    assert navlens.__version__ == workspace_version


def test_prediction_runtime_dependencies_are_required_by_distribution() -> None:
    requirements = requires("navlens") or []

    for package_name in ("numpy", "pandas", "scikit-learn"):
        assert any(requirement.startswith(package_name) for requirement in requirements)
