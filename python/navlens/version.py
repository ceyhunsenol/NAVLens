"""Installed NAVLens package version."""

from importlib.metadata import PackageNotFoundError, version


def installed_version() -> str:
    """Return package metadata version, or a source-tree fallback when not installed."""
    try:
        return version("navlens")
    except PackageNotFoundError:
        return "0+unknown"


__version__ = installed_version()
