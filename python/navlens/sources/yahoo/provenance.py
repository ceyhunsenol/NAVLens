"""Acquisition result and provenance metadata for Yahoo security prices."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from navlens._timestamps import validate_utc_timestamp
from navlens.datasets.security_price_snapshots import SecurityPriceSnapshot
from navlens.sources.artifact_digest import validate_sha256_hex

from .errors import YahooSecurityPriceSourceError


@dataclass(frozen=True, slots=True)
class YahooAcquisitionProvenance:
    """Provenance describing whether data came from network, cache, or fallback."""

    source_url: str
    retrieved_at: datetime
    sha256_hex: str
    is_from_cache: bool
    is_rate_limit_fallback: bool = False
    is_stale: bool = False
    payload_path: Path | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_url, str) or not self.source_url.strip():
            raise YahooSecurityPriceSourceError("source_url must be a non-empty string")
        validate_utc_timestamp(self.retrieved_at, "retrieved_at", YahooSecurityPriceSourceError)
        validate_sha256_hex(self.sha256_hex, "sha256_hex", YahooSecurityPriceSourceError)
        if (
            not isinstance(self.is_from_cache, bool)
            or not isinstance(self.is_rate_limit_fallback, bool)
            or not isinstance(self.is_stale, bool)
        ):
            raise YahooSecurityPriceSourceError("provenance flags must be booleans")
        if self.is_rate_limit_fallback and not self.is_from_cache:
            raise YahooSecurityPriceSourceError(
                "rate-limit fallback requires is_from_cache to be True"
            )
        if not self.is_from_cache and self.is_stale:
            raise YahooSecurityPriceSourceError("network response cannot be marked stale")
        if not self.is_rate_limit_fallback and self.is_stale:
            raise YahooSecurityPriceSourceError("regular cache hit cannot be marked stale")
        if self.payload_path is not None and not isinstance(self.payload_path, Path):
            raise YahooSecurityPriceSourceError("payload_path must be a Path instance or None")

    @property
    def is_stale_fallback(self) -> bool:
        """Return whether this result was acquired through a stale rate-limit fallback."""
        return self.is_rate_limit_fallback and self.is_stale


@dataclass(frozen=True, slots=True)
class YahooSecurityPriceAcquisitionResult:
    """Pair materialized snapshots with auditable acquisition provenance."""

    snapshots: tuple[SecurityPriceSnapshot, ...]
    provenance: YahooAcquisitionProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.snapshots, tuple) or not all(
            isinstance(snapshot, SecurityPriceSnapshot) for snapshot in self.snapshots
        ):
            raise YahooSecurityPriceSourceError(
                "snapshots must be a tuple of SecurityPriceSnapshot instances"
            )
        if not isinstance(self.provenance, YahooAcquisitionProvenance):
            raise YahooSecurityPriceSourceError(
                "provenance must be a YahooAcquisitionProvenance instance"
            )
