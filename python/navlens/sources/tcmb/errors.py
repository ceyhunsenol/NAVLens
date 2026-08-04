"""Errors raised by TCMB source capabilities."""


class TcmbXmlParseError(ValueError):
    """Raised when a TCMB XML payload cannot be parsed into provider records."""


class TcmbMappingError(ValueError):
    """Raised when TCMB daily rate records cannot be mapped into canonical FX observations."""


class TcmbTransportError(Exception):
    """Raised when a TCMB HTTP transport request fails."""
