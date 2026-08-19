"""Parsing of local provider-neutral CSV FX rate files."""

import csv
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

from navlens._native import (
    CurrencyCode,
    CurrencyPair,
    FxRate,
    FxRateKind,
    FxRateObservation,
    MarketDate,
)
from navlens.datasets.errors import FxRateDatasetError
from navlens.datasets.fx_rate_snapshots import FxRateSnapshot


class CsvFxRateSourceError(ValueError):
    """A CSV file cannot be mapped to valid FX rate snapshots."""


class CsvFxRateUnavailableError(CsvFxRateSourceError):
    """A CSV file cannot be accessed or read from the filesystem."""


REQUIRED_COLUMNS = frozenset(
    {
        "source_id",
        "base_currency",
        "quote_currency",
        "market_date",
        "rate",
        "kind",
        "available_at",
        "ingested_at",
    }
)

CsvRow = dict[str, str | None]


def read_fx_rates_csv(path: str | Path) -> list[FxRateSnapshot]:
    """Parse a provider-neutral CSV file into validated FxRateSnapshot objects."""
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
        raise CsvFxRateUnavailableError(f"cannot read CSV file {source_path}: {error}") from error

    if not rows:
        raise CsvFxRateSourceError(f"CSV file {source_path} contains no FX rate rows")
    return rows


def _validate_columns(fieldnames: Sequence[str] | None, path: Path) -> None:
    if fieldnames is None:
        raise CsvFxRateSourceError(f"CSV header is missing in {path}")
    missing = REQUIRED_COLUMNS.difference(fieldnames)
    if missing:
        names = ", ".join(sorted(missing))
        raise CsvFxRateSourceError(f"CSV is missing required columns in {path}: {names}")


def _parse_row(row: CsvRow, row_number: int, path: Path) -> FxRateSnapshot:
    source_id = _required_value(row, "source_id", row_number, path)
    available_text = _required_value(row, "available_at", row_number, path)
    ingested_text = _required_value(row, "ingested_at", row_number, path)

    observation = _parse_observation(row, row_number, path)
    available_at = _parse_timestamp(available_text, "available_at", row_number, path)
    ingested_at = _parse_timestamp(ingested_text, "ingested_at", row_number, path)

    try:
        return FxRateSnapshot(
            observation=observation,
            available_at=available_at,
            ingested_at=ingested_at,
            source_id=source_id,
        )
    except FxRateDatasetError as error:
        raise _row_error(path, row_number, str(error)) from error


def _parse_observation(row: CsvRow, row_number: int, path: Path) -> FxRateObservation:
    base_code = _parse_currency_code(
        _required_value(row, "base_currency", row_number, path), row_number, path
    )
    quote_code = _parse_currency_code(
        _required_value(row, "quote_currency", row_number, path), row_number, path
    )
    pair = _create_currency_pair(base_code, quote_code, row_number, path)

    market_date = _parse_market_date(
        _required_value(row, "market_date", row_number, path), row_number, path
    )
    rate = _parse_fx_rate(_required_value(row, "rate", row_number, path), row_number, path)
    kind = _parse_fx_rate_kind(_required_value(row, "kind", row_number, path), row_number, path)

    try:
        return FxRateObservation(pair, market_date, rate, kind)
    except ValueError as error:
        raise _row_error(path, row_number, str(error)) from error


def _create_currency_pair(
    base: CurrencyCode, quote: CurrencyCode, row_number: int, path: Path
) -> CurrencyPair:
    try:
        return CurrencyPair(base, quote)
    except ValueError as error:
        raise _row_error(path, row_number, str(error)) from error


def _parse_market_date(value: str, row_number: int, path: Path) -> MarketDate:
    try:
        parsed = date.fromisoformat(value)
        return MarketDate(parsed.year, parsed.month, parsed.day)
    except ValueError as error:
        raise _row_error(path, row_number, f"invalid ISO date {value!r}") from error


def _parse_fx_rate(value: str, row_number: int, path: Path) -> FxRate:
    try:
        float_val = float(value)
        return FxRate(float_val)
    except ValueError as error:
        raise _row_error(path, row_number, f"invalid rate {value!r}") from error


def _parse_currency_code(value: str, row_number: int, path: Path) -> CurrencyCode:
    try:
        return CurrencyCode(value)
    except ValueError as error:
        raise _row_error(path, row_number, f"invalid currency {value!r}") from error


def _parse_fx_rate_kind(value: str, row_number: int, path: Path) -> FxRateKind:
    try:
        return FxRateKind(value)
    except ValueError as error:
        raise _row_error(path, row_number, f"invalid kind {value!r}") from error


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


def _row_error(path: Path, row_number: int, message: str) -> CsvFxRateSourceError:
    return CsvFxRateSourceError(f"{path}:{row_number}: {message}")
