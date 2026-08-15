"""Caller-configured caching and rate-limit fallback policy for Yahoo acquisition."""

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class YahooAcquisitionPolicy:
    """Control cache freshness, force-refresh behavior, and rate-limit fallbacks."""

    cache_ttl: timedelta | None = timedelta(hours=24)
    allow_stale_on_429: bool = False
    force_refresh: bool = False

    def __post_init__(self) -> None:
        if self.cache_ttl is not None and (
            not isinstance(self.cache_ttl, timedelta)
            or isinstance(self.cache_ttl, bool)
            or self.cache_ttl < timedelta(0)
        ):
            raise ValueError("cache_ttl must be a non-negative timedelta or None")
        if not isinstance(self.allow_stale_on_429, bool):
            raise ValueError("allow_stale_on_429 must be a boolean")
        if not isinstance(self.force_refresh, bool):
            raise ValueError("force_refresh must be a boolean")
