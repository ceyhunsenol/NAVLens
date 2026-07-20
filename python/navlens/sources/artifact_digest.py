"""Digest calculation for immutable provider source artifacts."""

from hashlib import sha256
from pathlib import Path


def sha256_artifact(path: str | Path) -> str:
    """Return the hexadecimal SHA-256 digest of exact artifact bytes."""
    return sha256(Path(path).read_bytes()).hexdigest()
