"""Parsing of local provider-neutral CSV holdings files."""

import csv
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

from navlens._native import AssetClass, HoldingPosition, MarketDate
from navlens.datasets.errors import HoldingDatasetError
from navlens.datasets.holding_snapshots import HoldingSnapshot


class CsvHoldingsSourceError(ValueError):
    """A CSV file cannot be mapped to valid holdings snapshots."""


REQUIRED_COLUMNS = frozenset(
    {
        "fund_id",
        "effective_date",
        "published_at",
        "ingested_at",
        "source_id",
        "instrument_id",
        "asset_class",
        "weight",
    }
)

CsvRow = dict[str, str | None]
SnapshotKey = tuple[str, MarketDate, datetime, datetime, str]


def read_holdings_snapshots(path: str | Path) -> list[HoldingSnapshot]:
    """Parse a provider-neutral CSV file into validated HoldingSnapshot objects."""
    source_path = Path(path)
    rows = _read_rows(source_path)
    groups = _group_positions(rows, source_path)
    return [_build_snapshot(key, positions) for key, positions in groups.items()]


def _read_rows(source_path: Path) -> list[CsvRow]:
    try:
        with source_path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            _validate_columns(reader.fieldnames, source_path)
            rows = list(reader)
    except OSError as error:
        raise CsvHoldingsSourceError(f"cannot read CSV file {source_path}: {error}") from error

    if not rows:
        raise CsvHoldingsSourceError(f"CSV file {source_path} contains no holdings rows")
    return rows


def _group_positions(
    rows: list[CsvRow], source_path: Path
) -> dict[SnapshotKey, list[HoldingPosition]]:
    groups: dict[SnapshotKey, list[HoldingPosition]] = {}
    for row_number, row in enumerate(rows, start=2):
        metadata_key, position = _parse_row(row, row_number, source_path)
        groups.setdefault(metadata_key, []).append(position)
    return groups


def _build_snapshot(key: SnapshotKey, positions: list[HoldingPosition]) -> HoldingSnapshot:
    fund_id, effective_date, published_at, ingested_at, source_id = key
    try:
        return HoldingSnapshot(
            fund_id=fund_id,
            effective_date=effective_date,
            published_at=published_at,
            ingested_at=ingested_at,
            source_id=source_id,
            positions=tuple(positions),
        )
    except HoldingDatasetError as error:
        raise CsvHoldingsSourceError(f"invalid snapshot for fund '{fund_id}': {error}") from error


def _validate_columns(fieldnames: Sequence[str] | None, path: Path) -> None:
    if fieldnames is None:
        raise CsvHoldingsSourceError(f"CSV header is missing in {path}")
    missing = REQUIRED_COLUMNS.difference(fieldnames)
    if missing:
        names = ", ".join(sorted(missing))
        raise CsvHoldingsSourceError(f"CSV is missing required columns in {path}: {names}")


def _parse_row(row: CsvRow, row_number: int, path: Path) -> tuple[SnapshotKey, HoldingPosition]:
    metadata = _parse_metadata(row, row_number, path)
    position = _parse_position(row, row_number, path)
    return metadata, position


def _parse_metadata(row: CsvRow, row_number: int, path: Path) -> SnapshotKey:
    fund_id = _required_value(row, "fund_id", row_number, path)
    effective_text = _required_value(row, "effective_date", row_number, path)
    published_text = _required_value(row, "published_at", row_number, path)
    ingested_text = _required_value(row, "ingested_at", row_number, path)
    source_id = _required_value(row, "source_id", row_number, path)
    return (
        fund_id,
        _parse_effective_date(effective_text, row_number, path),
        _parse_timestamp(published_text, "published_at", row_number, path),
        _parse_timestamp(ingested_text, "ingested_at", row_number, path),
        source_id,
    )


def _parse_effective_date(value: str, row_number: int, path: Path) -> MarketDate:
    try:
        parsed = date.fromisoformat(value)
        return MarketDate(parsed.year, parsed.month, parsed.day)
    except ValueError as error:
        raise _row_error(path, row_number, f"invalid ISO date {value!r}") from error


def _parse_timestamp(value: str, field: str, row_number: int, path: Path) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise _row_error(path, row_number, f"invalid {field} timestamp {value!r}") from error


def _parse_position(row: CsvRow, row_number: int, path: Path) -> HoldingPosition:
    instrument_id = _required_value(row, "instrument_id", row_number, path)
    asset_class_text = _required_value(row, "asset_class", row_number, path)
    weight_text = _required_value(row, "weight", row_number, path)
    asset_class = _parse_asset_class(asset_class_text, row_number, path)
    weight = _parse_weight(weight_text, row_number, path)
    try:
        return HoldingPosition(instrument_id, asset_class, weight)
    except ValueError as error:
        raise _row_error(path, row_number, str(error)) from error


def _parse_weight(value: str, row_number: int, path: Path) -> float:
    try:
        return float(value)
    except ValueError as error:
        raise _row_error(path, row_number, f"invalid weight {value!r}") from error


def _parse_asset_class(value: str, row_number: int, path: Path) -> AssetClass:
    try:
        return AssetClass(value)
    except ValueError as error:
        raise _row_error(path, row_number, f"invalid asset_class {value!r}: {error}") from error


def _required_value(row: CsvRow, column: str, row_number: int, path: Path) -> str:
    value = row.get(column)
    if value is None or not value.strip():
        raise _row_error(path, row_number, f"{column} is required")
    return value.strip()


def _row_error(path: Path, row_number: int, message: str) -> CsvHoldingsSourceError:
    return CsvHoldingsSourceError(f"{path}:{row_number}: {message}")
