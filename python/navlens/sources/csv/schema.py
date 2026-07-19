"""Column contract for a single-fund unit-price CSV file."""

from collections.abc import Sequence

from .errors import CsvPriceSourceError

REQUIRED_COLUMNS = frozenset({"date", "unit_price"})


def validate_columns(fieldnames: Sequence[str] | None) -> None:
    if fieldnames is None:
        raise CsvPriceSourceError("CSV header is missing")
    missing = REQUIRED_COLUMNS.difference(fieldnames)
    if missing:
        names = ", ".join(sorted(missing))
        raise CsvPriceSourceError(f"CSV is missing required columns: {names}")
