"""Distribution metadata contract for release artifacts."""

import tomllib
from importlib.metadata import distribution, requires, version
from importlib.resources import files as resource_files
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


def test_release_metadata_exposes_public_project_contract() -> None:
    package_metadata = distribution("navlens").metadata

    assert package_metadata["License-Expression"] == "MIT"
    assert package_metadata["Requires-Python"] == ">=3.11"
    assert set(package_metadata.get_all("Project-URL") or ()) == {
        "Changelog, https://github.com/ceyhunsenol/NAVLens/blob/master/CHANGELOG.md",
        "Homepage, https://github.com/ceyhunsenol/NAVLens",
        "Issues, https://github.com/ceyhunsenol/NAVLens/issues",
        "Repository, https://github.com/ceyhunsenol/NAVLens",
    }

    classifiers = set(package_metadata.get_all("Classifier") or ())
    assert "Development Status :: 3 - Alpha" in classifiers
    assert "Typing :: Typed" in classifiers
    assert not any(classifier.startswith("License ::") for classifier in classifiers)


def test_distribution_contains_pep_561_marker() -> None:
    assert resource_files("navlens").joinpath("py.typed").is_file()
