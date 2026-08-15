"""Errors raised by the experimental Yahoo Finance source boundary."""


class YahooSecurityPriceSourceError(RuntimeError):
    """Base error for Yahoo security-price acquisition failures."""


class YahooSecurityPriceRequestError(YahooSecurityPriceSourceError):
    """A Yahoo security-price request violates its local contract."""


class YahooSecurityPriceTransportError(YahooSecurityPriceSourceError):
    """The Yahoo chart endpoint could not be reached successfully."""


class YahooSecurityPriceRateLimitError(YahooSecurityPriceTransportError):
    """Yahoo rejected the request because its current rate limit was reached."""

    def __init__(self, message: str, retry_after: str | None = None) -> None:
        if retry_after is not None and not isinstance(retry_after, str):
            raise TypeError("retry_after must be a string or None")
        super().__init__(message)
        self.retry_after = retry_after

    @property
    def retry_after_seconds(self) -> int | None:
        """Return the parsed delay in seconds if Retry-After is a non-negative decimal integer."""
        if self.retry_after is None:
            return None
        stripped = self.retry_after.strip()
        if stripped and stripped.isascii() and stripped.isdigit():
            return int(stripped)
        return None


class YahooSecurityPricePayloadError(YahooSecurityPriceSourceError):
    """A Yahoo chart response violates the expected provider schema."""


class YahooSecurityPriceCacheError(YahooSecurityPriceSourceError):
    """Base error for Yahoo security-price raw cache storage or access failures."""


class YahooSecurityPriceCacheIntegrityError(YahooSecurityPriceCacheError):
    """A cached Yahoo payload digest, sidecar metadata, or pairing violates integrity invariants."""


class YahooSecurityPriceBatchError(YahooSecurityPriceSourceError):
    """A Yahoo security-price batch violates its local execution contract."""
