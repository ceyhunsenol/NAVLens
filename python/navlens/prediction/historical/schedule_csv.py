"""Provider-neutral CSV reader for historical prediction schedules."""

import csv
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

from navlens import MarketDate
from navlens._timestamps import validate_utc_timestamp

from .errors import HistoricalPredictionDatasetError
from .request import HistoricalPredictionRequest


class CsvHistoricalPredictionScheduleSourceError(ValueError):
    """A CSV file cannot be mapped to valid historical prediction requests."""


REQUIRED_COLUMNS = frozenset(
    {
        "prediction_date",
        "pricing_as_of_date",
        "target_date",
        "prediction_timestamp",
        "evaluation_timestamp",
    }
)

CsvRow = dict[str, str | None]


def read_historical_prediction_requests_csv(
    path: str | Path,
) -> list[HistoricalPredictionRequest]:
    """Parse a historical prediction schedule into validated requests."""
    source_path = Path(path)
    rows = _read_rows(source_path)
    return [_parse_request(row, row_number, source_path) for row_number, row in rows]


def _read_rows(source_path: Path) -> list[tuple[int, CsvRow]]:
    try:
        with source_path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            _validate_columns(reader.fieldnames, source_path)
            rows = [(reader.line_num, row) for row in reader]
    except OSError as error:
        raise CsvHistoricalPredictionScheduleSourceError(
            f"cannot read historical prediction schedule {source_path}: {error}"
        ) from error

    if not rows:
        raise CsvHistoricalPredictionScheduleSourceError(
            f"historical prediction schedule {source_path} contains no rows"
        )
    return rows


def _validate_columns(fieldnames: Sequence[str] | None, source_path: Path) -> None:
    if fieldnames is None:
        raise CsvHistoricalPredictionScheduleSourceError(
            f"CSV header is missing in historical prediction schedule {source_path}"
        )
    missing = sorted(REQUIRED_COLUMNS.difference(fieldnames))
    if missing:
        names = ", ".join(missing)
        raise CsvHistoricalPredictionScheduleSourceError(
            f"historical prediction schedule {source_path} is missing required columns: {names}"
        )


def _parse_request(
    row: CsvRow,
    row_number: int,
    source_path: Path,
) -> HistoricalPredictionRequest:
    try:
        return HistoricalPredictionRequest(
            prediction_date=_parse_market_date(
                _required(row, "prediction_date", row_number, source_path)
            ),
            pricing_as_of_date=_parse_market_date(
                _required(row, "pricing_as_of_date", row_number, source_path)
            ),
            target_date=_parse_market_date(_required(row, "target_date", row_number, source_path)),
            prediction_timestamp=_parse_utc_datetime(
                _required(row, "prediction_timestamp", row_number, source_path),
                "prediction_timestamp",
            ),
            evaluation_timestamp=_parse_utc_datetime(
                _required(row, "evaluation_timestamp", row_number, source_path),
                "evaluation_timestamp",
            ),
        )
    except (ValueError, HistoricalPredictionDatasetError) as error:
        if isinstance(error, CsvHistoricalPredictionScheduleSourceError):
            raise
        raise _row_error(source_path, row_number, str(error)) from error


def _required(row: CsvRow, field: str, row_number: int, source_path: Path) -> str:
    value = row.get(field)
    if value is None or not value.strip():
        raise _row_error(source_path, row_number, f"{field} is required")
    return value.strip()


def _parse_market_date(value: str) -> MarketDate:
    if len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise ValueError(f"date must use YYYY-MM-DD format, got {value!r}")
    parsed = date.fromisoformat(value)
    return MarketDate(parsed.year, parsed.month, parsed.day)


def _parse_utc_datetime(value: str, field: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    validate_utc_timestamp(parsed, field, ValueError)
    return parsed


def _row_error(
    source_path: Path,
    row_number: int,
    message: str,
) -> CsvHistoricalPredictionScheduleSourceError:
    return CsvHistoricalPredictionScheduleSourceError(
        f"cannot parse historical prediction schedule {source_path} at row {row_number}: {message}"
    )
