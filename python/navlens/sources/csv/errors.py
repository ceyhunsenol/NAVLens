"""Errors raised while reading the external CSV representation."""


class CsvPriceSourceError(ValueError):
    """A CSV file cannot be mapped to explicit price records."""
