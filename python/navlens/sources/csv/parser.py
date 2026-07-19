"""Parsing of the external single-fund CSV price format."""

import csv
from datetime import date
from pathlib import Path

from .errors import CsvPriceSourceError
from .records import CsvPriceRecord
from .schema import validate_columns


def read_price_records(path: str | Path) -> list[CsvPriceRecord]:
    source_path = Path(path)
    try:
        with source_path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            validate_columns(reader.fieldnames)
            records = [
                _parse_row(row, row_number, source_path)
                for row_number, row in enumerate(reader, start=2)
            ]
    except OSError as error:
        raise CsvPriceSourceError(f"cannot read CSV file {source_path}: {error}") from error

    if not records:
        raise CsvPriceSourceError(f"CSV file {source_path} contains no price rows")
    return records


def _parse_row(row: dict[str, str | None], row_number: int, path: Path) -> CsvPriceRecord:
    date_text = _required_value(row, "date", row_number, path)
    price_text = _required_value(row, "unit_price", row_number, path)
    try:
        market_date = date.fromisoformat(date_text)
    except ValueError as error:
        raise _row_error(path, row_number, f"invalid ISO date {date_text!r}") from error
    try:
        unit_price = float(price_text)
    except ValueError as error:
        raise _row_error(path, row_number, f"invalid unit price {price_text!r}") from error
    return CsvPriceRecord(market_date=market_date, unit_price=unit_price)


def _required_value(
    row: dict[str, str | None],
    column: str,
    row_number: int,
    path: Path,
) -> str:
    value = row.get(column)
    if value is None or not value.strip():
        raise _row_error(path, row_number, f"{column} is required")
    return value.strip()


def _row_error(path: Path, row_number: int, message: str) -> CsvPriceSourceError:
    return CsvPriceSourceError(f"{path}:{row_number}: {message}")
