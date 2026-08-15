"""Validated in-memory representation of a cached Yahoo chart response."""

from dataclasses import dataclass
from datetime import datetime

from navlens._timestamps import validate_utc_timestamp
from navlens.sources.artifact_digest import sha256_bytes, validate_sha256_hex

from .cache_identity import YahooCacheIdentity
from .errors import YahooSecurityPriceCacheError, YahooSecurityPriceCacheIntegrityError


@dataclass(frozen=True, slots=True)
class YahooCacheRecord:
    """Exact raw response bytes paired with validated metadata and identity."""

    identity: YahooCacheIdentity
    source_url: str
    retrieved_at: datetime
    sha256_hex: str
    byte_count: int
    body: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.identity, YahooCacheIdentity):
            raise YahooSecurityPriceCacheError("identity must be a YahooCacheIdentity")
        if not isinstance(self.source_url, str) or not self.source_url.strip():
            raise YahooSecurityPriceCacheError("source_url must be a non-empty string")
        validate_utc_timestamp(self.retrieved_at, "retrieved_at", YahooSecurityPriceCacheError)
        validate_sha256_hex(self.sha256_hex, "sha256_hex", YahooSecurityPriceCacheError)
        if (
            type(self.byte_count) is not int
            or isinstance(self.byte_count, bool)
            or self.byte_count < 0
        ):
            raise YahooSecurityPriceCacheError("byte_count must be a non-negative integer")
        if not isinstance(self.body, bytes):
            raise YahooSecurityPriceCacheError("body must be bytes")
        if len(self.body) != self.byte_count:
            raise YahooSecurityPriceCacheError("byte_count does not match body length")
        if sha256_bytes(self.body) != self.sha256_hex:
            raise YahooSecurityPriceCacheIntegrityError("sha256_hex does not match body digest")
