"""Content-addressed atomic storage for raw TCMB response payloads."""

from dataclasses import dataclass
from pathlib import Path

from navlens.sources.artifact_digest import sha256_bytes, validate_sha256_hex
from navlens.storage.atomic import atomic_write_bytes

from .acquisition import TcmbAcquiredDailyRates
from .errors import TcmbRawCacheError, TcmbRawCacheIntegrityError


@dataclass(frozen=True, slots=True)
class TcmbRawCacheEntry:
    """A record of a stored or discovered raw TCMB artifact."""

    sha256_hex: str
    path: Path
    byte_count: int
    already_present: bool

    def __post_init__(self) -> None:
        validate_sha256_hex(self.sha256_hex, "sha256_hex", TcmbRawCacheError)
        if not isinstance(self.path, Path):
            raise TcmbRawCacheError("path must be a pathlib.Path")
        if (
            not isinstance(self.byte_count, int)
            or isinstance(self.byte_count, bool)
            or self.byte_count < 0
        ):
            raise TcmbRawCacheError("byte_count must be a non-negative integer")
        if not isinstance(self.already_present, bool):
            raise TcmbRawCacheError("already_present must be a boolean")


def _get_cache_path(root: Path, sha256_hex: str) -> Path:
    validate_sha256_hex(sha256_hex, "sha256_hex", TcmbRawCacheError)
    return root / "tcmb" / "raw" / "sha256" / sha256_hex[:2] / f"{sha256_hex}.xml"


def store_tcmb_raw_artifact(
    root: str | Path,
    acquisition: TcmbAcquiredDailyRates,
) -> TcmbRawCacheEntry:
    """Atomically store exact bytes without replacing an existing valid artifact."""
    root_path = Path(root)
    sha256_hex = acquisition.provenance.sha256_hex

    actual_digest = sha256_bytes(acquisition.raw_body)
    if actual_digest != sha256_hex:
        raise TcmbRawCacheError("acquisition raw_body digest does not match provenance sha256_hex")

    target_path = _get_cache_path(root_path, sha256_hex)

    if target_path.exists():
        existing_bytes = target_path.read_bytes()
        existing_digest = sha256_bytes(existing_bytes)
        if existing_digest != sha256_hex:
            raise TcmbRawCacheIntegrityError(f"existing file at {target_path} is corrupted")

        return TcmbRawCacheEntry(
            sha256_hex=sha256_hex,
            path=target_path,
            byte_count=len(acquisition.raw_body),
            already_present=True,
        )

    atomic_write_bytes(target_path, acquisition.raw_body)

    return TcmbRawCacheEntry(
        sha256_hex=sha256_hex,
        path=target_path,
        byte_count=len(acquisition.raw_body),
        already_present=False,
    )


def load_tcmb_raw_artifact(
    root: str | Path,
    sha256_hex: str,
) -> bytes | None:
    """Load exact bytes and verify them against their content address."""
    root_path = Path(root)
    target_path = _get_cache_path(root_path, sha256_hex)

    if not target_path.exists():
        return None

    content = target_path.read_bytes()
    actual_digest = sha256_bytes(content)
    if actual_digest != sha256_hex:
        raise TcmbRawCacheIntegrityError(f"loaded file at {target_path} is corrupted")

    return content
