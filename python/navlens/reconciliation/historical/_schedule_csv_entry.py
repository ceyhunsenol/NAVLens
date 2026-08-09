"""Private schedule CSV row reader and typed entry representation."""

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from navlens import MarketDate, ReturnPeriod
from navlens._timestamps import validate_utc_timestamp


class CsvHistoricalScheduleSourceError(ValueError):
    """A CSV file cannot be mapped to valid historical reconciliation requests."""


REQUIRED_COLUMNS = frozenset(
    {
        "return_start_date",
        "return_end_date",
        "pricing_as_of_date",
        "prediction_timestamp",
    }
)


@dataclass(frozen=True, slots=True)
class ScheduleCsvEntry:
    """Immutable parsed schedule row with physical line number metadata."""

    period: ReturnPeriod
    pricing_as_of_date: MarketDate
    prediction_timestamp: datetime
    physical_line_number: int


def read_schedule_csv_entries(source_path: Path) -> list[ScheduleCsvEntry]:
    """Read and parse a schedule CSV file into immutable ScheduleCsvEntry objects."""
    raw_rows = _read_raw_schedule_rows(source_path)

    entries: list[ScheduleCsvEntry] = []
    for line_num, row in raw_rows:
        entry = _parse_schedule_entry(row, line_num, source_path)
        entries.append(entry)

    return entries


def _read_raw_schedule_rows(source_path: Path) -> list[tuple[int, dict[str, str]]]:
    try:
        with source_path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None:
                raise CsvHistoricalScheduleSourceError(f"empty schedule CSV file: {source_path}")

            missing_columns = sorted(REQUIRED_COLUMNS - set(reader.fieldnames))
            if missing_columns:
                cols_str = ", ".join(f"'{c}'" for c in missing_columns)
                raise CsvHistoricalScheduleSourceError(
                    f"cannot parse schedule CSV {source_path} at row 1: "
                    f"missing required columns: {cols_str}"
                )

            rows: list[tuple[int, dict[str, str]]] = []
            for row in reader:
                rows.append((reader.line_num, row))
    except OSError as error:
        raise OSError(f"cannot read CSV file {source_path}: {error}") from error

    if not rows:
        raise CsvHistoricalScheduleSourceError(f"empty schedule CSV file: {source_path}")

    return rows


def _parse_schedule_entry(
    row: dict[str, str],
    line_number: int,
    source_path: Path,
) -> ScheduleCsvEntry:
    for col in (
        "return_start_date",
        "return_end_date",
        "pricing_as_of_date",
        "prediction_timestamp",
    ):
        val = row.get(col)
        if val is None or not val.strip():
            raise CsvHistoricalScheduleSourceError(
                f"cannot parse schedule CSV {source_path} at row {line_number}: "
                f"missing required value for '{col}'"
            )

    try:
        start_date = _parse_date(row["return_start_date"])
        end_date = _parse_date(row["return_end_date"])
        pricing_as_of = _parse_date(row["pricing_as_of_date"])
        prediction_ts = _parse_utc_datetime(row["prediction_timestamp"])

        period = ReturnPeriod(start_date, end_date)
        return ScheduleCsvEntry(
            period=period,
            pricing_as_of_date=pricing_as_of,
            prediction_timestamp=prediction_ts,
            physical_line_number=line_number,
        )
    except ValueError as error:
        if isinstance(error, CsvHistoricalScheduleSourceError):
            raise
        raise CsvHistoricalScheduleSourceError(
            f"cannot parse schedule CSV {source_path} at row {line_number}: {error}"
        ) from error


def _parse_date(val: str) -> MarketDate:
    raw = val.strip()
    if len(raw) != 10 or raw[4] != "-" or raw[7] != "-":
        raise ValueError(f"date must be YYYY-MM-DD format, got {val!r}")
    parsed = date.fromisoformat(raw)
    return MarketDate(parsed.year, parsed.month, parsed.day)


def _parse_utc_datetime(val: str) -> datetime:
    raw = val.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(raw)
    validate_utc_timestamp(dt, "prediction_timestamp", ValueError)
    return dt
