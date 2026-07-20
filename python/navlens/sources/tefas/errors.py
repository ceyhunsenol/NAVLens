"""Errors raised at the TEFAS acquisition boundary."""


class TefasSourceError(RuntimeError):
    """Base error for TEFAS transport and export failures."""


class TefasRequestError(TefasSourceError):
    """Raised when a price request cannot describe a supported query."""


class TefasTransportError(TefasSourceError):
    """Raised when TEFAS cannot be reached or returns an HTTP failure."""


class TefasPayloadError(TefasSourceError):
    """Raised when a TEFAS JSON payload violates the provider schema."""
