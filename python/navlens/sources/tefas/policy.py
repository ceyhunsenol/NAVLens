"""Conservative access policy for TEFAS HTTP acquisition."""

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class TefasAccessPolicy:
    """Bound request frequency, caching, and retry behavior."""

    minimum_interval: timedelta = timedelta(seconds=5)
    cache_ttl: timedelta = timedelta(hours=24)
    maximum_attempts: int = 3
    maximum_concurrency: int = 1
    retry_base_delay: timedelta = timedelta(seconds=2)

    def __post_init__(self) -> None:
        if self.minimum_interval <= timedelta(0):
            raise ValueError("minimum interval must be positive")
        if self.cache_ttl <= timedelta(0):
            raise ValueError("cache TTL must be positive")
        if self.maximum_attempts < 1:
            raise ValueError("maximum attempts must be positive")
        if self.maximum_concurrency != 1:
            raise ValueError("TEFAS concurrency must remain one")
        if self.retry_base_delay <= timedelta(0):
            raise ValueError("retry base delay must be positive")

    def retry_delay(self, failed_attempt: int) -> timedelta:
        """Return exponential delay after a one-based failed attempt."""
        if failed_attempt < 1 or failed_attempt >= self.maximum_attempts:
            raise ValueError("failed attempt has no retry")
        return self.retry_base_delay * (2 ** (failed_attempt - 1))
