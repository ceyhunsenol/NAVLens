"""Digest calculation for immutable provider source artifacts."""

from hashlib import sha256
from pathlib import Path


def sha256_bytes(payload: bytes) -> str:
    """Return the hexadecimal SHA-256 digest of exact raw payload bytes."""
    return sha256(payload).hexdigest()


def sha256_artifact(path: str | Path) -> str:
    """Return the hexadecimal SHA-256 digest of exact artifact bytes."""
    return sha256_bytes(Path(path).read_bytes())


def validate_sha256_hex(value: str, field_name: str, error_type: type[Exception]) -> None:
    """Validate that a string is a 64-character lowercase hex digest."""
    if (
        not isinstance(value, str)
        or len(value) != 64
        or not all(character in "0123456789abcdef" for character in value)
    ):
        raise error_type(f"{field_name} must be a 64-character lowercase hex string")
