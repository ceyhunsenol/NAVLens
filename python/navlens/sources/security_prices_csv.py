"""Parsing of local provider-neutral CSV security price files."""

import csv
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

from navlens._native import (
    CurrencyCode,
    MarketDate,
    PriceAdjustment,
    SecurityPriceObservation,
    UnitPrice,
)
from navlens.datasets.errors import SecurityPriceDatasetError
from navlens.datasets.security_price_snapshots import SecurityPriceSnapshot


class CsvSecurityPriceSourceError(ValueError):
    """A CSV file cannot be mapped to valid security price snapshots."""


REQUIRED_COLUMNS = frozenset(
    {
        "source_id",
        "instrument_id",
        "market_date",
        "price",
        "currency",
        "adjustment",
        "available_at",
        "ingested_at",
    }
)

CsvRow = dict[str, str | None]


def read_security_prices_csv(path: str | Path) -> list[SecurityPriceSnapshot]:
    """Parse a provider-neutral CSV file into validated SecurityPriceSnapshot objects."""
    source_path = Path(path)
    rows = _read_rows(source_path)
    return [
        _parse_row(row, row_number, source_path) for row_number, row in enumerate(rows, start=2)
    ]


def _read_rows(source_path: Path) -> list[CsvRow]:
    try:
        with source_path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            _validate_columns(reader.fieldnames, source_path)
            rows = list(reader)
    except OSError as error:
        raise CsvSecurityPriceSourceError(f"cannot read CSV file {source_path}: {error}") from error

    if not rows:
        raise CsvSecurityPriceSourceError(f"CSV file {source_path} contains no security price rows")
    return rows


def _validate_columns(fieldnames: Sequence[str] | None, path: Path) -> None:
    if fieldnames is None:
        raise CsvSecurityPriceSourceError(f"CSV header is missing in {path}")
    missing = REQUIRED_COLUMNS.difference(fieldnames)
    if missing:
        names = ", ".join(sorted(missing))
        raise CsvSecurityPriceSourceError(f"CSV is missing required columns in {path}: {names}")


def _parse_row(row: CsvRow, row_number: int, path: Path) -> SecurityPriceSnapshot:
    source_id = _required_value(row, "source_id", row_number, path)
    available_text = _required_value(row, "available_at", row_number, path)
    ingested_text = _required_value(row, "ingested_at", row_number, path)

    observation = _parse_observation(row, row_number, path)
    available_at = _parse_timestamp(available_text, "available_at", row_number, path)
    ingested_at = _parse_timestamp(ingested_text, "ingested_at", row_number, path)

    try:
        return SecurityPriceSnapshot(
            observation=observation,
            available_at=available_at,
            ingested_at=ingested_at,
            source_id=source_id,
        )
    except SecurityPriceDatasetError as error:
        raise _row_error(path, row_number, str(error)) from error


def _parse_observation(row: CsvRow, row_number: int, path: Path) -> SecurityPriceObservation:
    instrument_id = _required_value(row, "instrument_id", row_number, path)
    market_date = _parse_market_date(
        _required_value(row, "market_date", row_number, path), row_number, path
    )
    unit_price = _parse_unit_price(
        _required_value(row, "price", row_number, path), row_number, path
    )
    currency_code = _parse_currency_code(
        _required_value(row, "currency", row_number, path), row_number, path
    )
    price_adjustment = _parse_price_adjustment(
        _required_value(row, "adjustment", row_number, path), row_number, path
    )
    try:
        return SecurityPriceObservation(
            instrument_id, market_date, unit_price, currency_code, price_adjustment
        )
    except ValueError as error:
        raise _row_error(path, row_number, str(error)) from error


def _parse_market_date(value: str, row_number: int, path: Path) -> MarketDate:
    try:
        parsed = date.fromisoformat(value)
        return MarketDate(parsed.year, parsed.month, parsed.day)
    except ValueError as error:
        raise _row_error(path, row_number, f"invalid ISO date {value!r}") from error


def _parse_unit_price(value: str, row_number: int, path: Path) -> UnitPrice:
    try:
        float_val = float(value)
        return UnitPrice(float_val)
    except ValueError as error:
        raise _row_error(path, row_number, f"invalid price {value!r}") from error


def _parse_currency_code(value: str, row_number: int, path: Path) -> CurrencyCode:
    try:
        return CurrencyCode(value)
    except ValueError as error:
        raise _row_error(path, row_number, f"invalid currency {value!r}") from error


def _parse_price_adjustment(value: str, row_number: int, path: Path) -> PriceAdjustment:
    try:
        return PriceAdjustment(value)
    except ValueError as error:
        raise _row_error(path, row_number, f"invalid adjustment {value!r}") from error


def _parse_timestamp(value: str, field: str, row_number: int, path: Path) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise _row_error(path, row_number, f"invalid {field} timestamp {value!r}") from error


def _required_value(row: CsvRow, column: str, row_number: int, path: Path) -> str:
    value = row.get(column)
    if value is None or not value.strip():
        raise _row_error(path, row_number, f"{column} is required")
    return value.strip()


def _row_error(path: Path, row_number: int, message: str) -> CsvSecurityPriceSourceError:
    return CsvSecurityPriceSourceError(f"{path}:{row_number}: {message}")
