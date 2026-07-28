"""Parsing of local provider-neutral CSV fund unit-price files."""

import csv
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

from navlens._native import (
    MarketDate,
    PriceObservation,
    UnitPrice,
)
from navlens.datasets.errors import FundUnitPriceDatasetError
from navlens.datasets.fund_unit_price_snapshots import FundUnitPriceSnapshot


class CsvFundUnitPriceSourceError(ValueError):
    """A CSV file cannot be mapped to valid fund unit-price snapshots."""


REQUIRED_COLUMNS = frozenset(
    {
        "fund_id",
        "market_date",
        "unit_price",
        "available_at",
        "ingested_at",
        "source_id",
    }
)

CsvRow = dict[str, str | None]


def read_fund_unit_prices_csv(path: str | Path) -> list[FundUnitPriceSnapshot]:
    """Parse a provider-neutral CSV file into validated FundUnitPriceSnapshot objects."""
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
        raise CsvFundUnitPriceSourceError(f"cannot read CSV file {source_path}: {error}") from error

    if not rows:
        raise CsvFundUnitPriceSourceError(
            f"CSV file {source_path} contains no fund unit-price rows"
        )
    return rows


def _validate_columns(fieldnames: Sequence[str] | None, path: Path) -> None:
    if fieldnames is None:
        raise CsvFundUnitPriceSourceError(f"CSV header is missing in {path}")
    missing = REQUIRED_COLUMNS.difference(fieldnames)
    if missing:
        names = ", ".join(sorted(missing))
        raise CsvFundUnitPriceSourceError(f"CSV is missing required columns in {path}: {names}")


def _parse_row(row: CsvRow, row_number: int, path: Path) -> FundUnitPriceSnapshot:
    source_id = _required_value(row, "source_id", row_number, path)
    fund_id = _required_value(row, "fund_id", row_number, path)
    available_text = _required_value(row, "available_at", row_number, path)
    ingested_text = _required_value(row, "ingested_at", row_number, path)

    observation = _parse_observation(row, row_number, path)
    available_at = _parse_timestamp(available_text, "available_at", row_number, path)
    ingested_at = _parse_timestamp(ingested_text, "ingested_at", row_number, path)

    try:
        return FundUnitPriceSnapshot(
            fund_id=fund_id,
            observation=observation,
            available_at=available_at,
            ingested_at=ingested_at,
            source_id=source_id,
        )
    except FundUnitPriceDatasetError as error:
        raise _row_error(path, row_number, str(error)) from error


def _parse_observation(row: CsvRow, row_number: int, path: Path) -> PriceObservation:
    market_date = _parse_market_date(
        _required_value(row, "market_date", row_number, path), row_number, path
    )
    unit_price = _parse_unit_price(
        _required_value(row, "unit_price", row_number, path), row_number, path
    )
    try:
        return PriceObservation(market_date, unit_price)
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


def _row_error(path: Path, row_number: int, message: str) -> CsvFundUnitPriceSourceError:
    return CsvFundUnitPriceSourceError(f"{path}:{row_number}: {message}")
