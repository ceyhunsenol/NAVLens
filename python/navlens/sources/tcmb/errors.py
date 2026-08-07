"""Errors raised by TCMB source capabilities."""


class TcmbXmlParseError(ValueError):
    """Raised when a TCMB XML payload cannot be parsed into provider records."""


class TcmbMappingError(ValueError):
    """Raised when TCMB daily rate records cannot be mapped into canonical FX observations."""


class TcmbTransportError(Exception):
    """Raised when a TCMB HTTP transport request fails."""


class TcmbAcquisitionError(ValueError):
    """Raised when TCMB acquisition provenance invariants are violated."""


class TcmbRawCacheError(ValueError):
    """Raised for invalid parameters when interacting with the TCMB raw cache."""


class TcmbRawCacheIntegrityError(TcmbRawCacheError):
    """Raised when TCMB raw cache content does not match its expected digest."""


class TcmbRevisionIndexError(ValueError):
    """Raised for invalid parameters or states when interacting with the TCMB revision index."""


class TcmbRevisionIndexIntegrityError(TcmbRevisionIndexError):
    """Raised when a TCMB revision index on disk is malformed, invalid, or corrupt."""


class TcmbRevisionAvailabilityError(ValueError):
    """Raised for invalid parameters or states when resolving revision availability."""
