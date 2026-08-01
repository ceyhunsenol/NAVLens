"""Errors raised while parsing TCMB XML payloads."""


class TcmbXmlParseError(ValueError):
    """Raised when a TCMB XML payload cannot be parsed into provider records."""
