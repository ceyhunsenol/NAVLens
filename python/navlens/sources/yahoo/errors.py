"""Errors raised by the experimental Yahoo Finance source boundary."""


class YahooSecurityPriceSourceError(RuntimeError):
    """Base error for Yahoo security-price acquisition failures."""


class YahooSecurityPriceRequestError(YahooSecurityPriceSourceError):
    """A Yahoo security-price request violates its local contract."""


class YahooSecurityPriceTransportError(YahooSecurityPriceSourceError):
    """The Yahoo chart endpoint could not be reached successfully."""


class YahooSecurityPriceRateLimitError(YahooSecurityPriceTransportError):
    """Yahoo rejected the request because its current rate limit was reached."""


class YahooSecurityPricePayloadError(YahooSecurityPriceSourceError):
    """A Yahoo chart response violates the expected provider schema."""
