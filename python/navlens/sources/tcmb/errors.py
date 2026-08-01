"""Errors raised while parsing TCMB XML payloads."""


class TcmbXmlParseError(ValueError):
    """Raised when a TCMB XML payload cannot be parsed into provider records."""


class TcmbMappingError(ValueError):
    """Raised when TCMB daily rate records cannot be mapped into canonical FX observations."""
