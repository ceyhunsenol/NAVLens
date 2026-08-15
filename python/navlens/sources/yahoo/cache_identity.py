"""Deterministic cache identity and path derivation for Yahoo chart payloads."""

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from navlens.sources.artifact_digest import sha256_bytes

from .errors import YahooSecurityPriceCacheError
from .request import YahooSecurityPriceRequest
from .snapshots import YAHOO_SOURCE_ID

YAHOO_CACHE_SCHEMA_VERSION: int = 1


@dataclass(frozen=True, slots=True)
class YahooCacheIdentity:
    """Canonical request-derived cache identity."""

    provider: str
    symbol: str
    start_date: date
    end_date: date
    schema_version: int = YAHOO_CACHE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise YahooSecurityPriceCacheError("provider must be a non-empty string")
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise YahooSecurityPriceCacheError("symbol must be a non-empty string")
        if type(self.start_date) is not date or type(self.end_date) is not date:
            raise YahooSecurityPriceCacheError("start_date and end_date must be date instances")
        if self.start_date > self.end_date:
            raise YahooSecurityPriceCacheError("start_date must not be after end_date")
        if (
            type(self.schema_version) is not int
            or isinstance(self.schema_version, bool)
            or self.schema_version < 1
        ):
            raise YahooSecurityPriceCacheError("schema_version must be a positive integer")

    def digest(self) -> str:
        """Return the deterministic SHA-256 digest of this canonical identity."""
        data = {
            "end_date": self.end_date.isoformat(),
            "provider": self.provider,
            "schema_version": self.schema_version,
            "start_date": self.start_date.isoformat(),
            "symbol": self.symbol,
        }
        encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256_bytes(encoded)


@dataclass(frozen=True, slots=True)
class YahooCachePaths:
    """Locate one raw Yahoo response artifact and its metadata sidecar."""

    payload: Path
    metadata: Path

    def __post_init__(self) -> None:
        if not isinstance(self.payload, Path) or not isinstance(self.metadata, Path):
            raise YahooSecurityPriceCacheError("payload and metadata must be Path instances")


def build_cache_paths(root: str | Path, request: YahooSecurityPriceRequest) -> YahooCachePaths:
    """Derive deterministic cache paths without embedding untrusted symbols."""
    if not isinstance(root, (str, Path)):
        raise YahooSecurityPriceCacheError("root must be a string or Path")
    if not isinstance(request, YahooSecurityPriceRequest):
        raise YahooSecurityPriceCacheError("request must be a YahooSecurityPriceRequest")

    identity = YahooCacheIdentity(
        provider=YAHOO_SOURCE_ID,
        symbol=request.mapping.normalized_provider_symbol,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    stem = (
        f"chart-{identity.start_date.isoformat()}-"
        f"{identity.end_date.isoformat()}-{identity.digest()[:16]}"
    )
    directory = Path(root)
    return YahooCachePaths(
        payload=directory / f"{stem}.json",
        metadata=directory / f"{stem}.metadata.json",
    )
