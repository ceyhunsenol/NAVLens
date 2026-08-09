"""Parsing of provider-neutral historical reconciliation schedule CSV files."""

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from navlens import (
    AlignmentPolicy,
    CurrencyCode,
    MarketDate,
    PriceAdjustment,
    ReturnPeriod,
)
from navlens._timestamps import validate_utc_timestamp
from navlens.alignment import PointInTimeAlignmentRequest
from navlens.alignment.errors import PointInTimeAlignmentError

from .errors import (
    HistoricalReconciliationDatasetError,
    InvalidHistoricalReconciliationRunConfigurationError,
)
from .request import HistoricalReconciliationRequest


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
class HistoricalReconciliationRunConfiguration:
    """Static financial policy and source configuration shared across schedule rows."""

    fund_id: str
    holdings_source_id: str
    security_price_source_id: str
    fund_price_source_id: str
    fund_base_currency: CurrencyCode
    required_price_adjustment: PriceAdjustment
    minimum_observations: int
    max_staleness_calendar_days: int

    def __post_init__(self) -> None:
        """Validate structural type and parameter invariants upon construction."""
        if not isinstance(self.fund_base_currency, CurrencyCode):
            raise TypeError(
                "fund_base_currency must be a CurrencyCode instance, "
                f"got {type(self.fund_base_currency).__name__}"
            )
        if not isinstance(self.required_price_adjustment, PriceAdjustment):
            raise TypeError(
                "required_price_adjustment must be a PriceAdjustment instance, "
                f"got {type(self.required_price_adjustment).__name__}"
            )

        for name, value in (
            ("fund_id", self.fund_id),
            ("holdings_source_id", self.holdings_source_id),
            ("security_price_source_id", self.security_price_source_id),
            ("fund_price_source_id", self.fund_price_source_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise InvalidHistoricalReconciliationRunConfigurationError(
                    f"{name} must be a non-empty string, got {value!r}"
                )

        for name, value in (
            ("minimum_observations", self.minimum_observations),
            ("max_staleness_calendar_days", self.max_staleness_calendar_days),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be a non-bool integer, got {value!r}")

        if self.minimum_observations < 2:
            raise InvalidHistoricalReconciliationRunConfigurationError(
                f"minimum_observations must be at least 2, got {self.minimum_observations}"
            )

        if self.max_staleness_calendar_days < 0:
            raise InvalidHistoricalReconciliationRunConfigurationError(
                "max_staleness_calendar_days must be non-negative, "
                f"got {self.max_staleness_calendar_days}"
            )


def read_historical_reconciliation_requests_csv(
    path: str | Path,
    config: HistoricalReconciliationRunConfiguration,
) -> list[HistoricalReconciliationRequest]:
    """Parse a historical schedule CSV file into HistoricalReconciliationRequest instances."""
    if not isinstance(config, HistoricalReconciliationRunConfiguration):
        target_type = type(config).__name__
        raise TypeError(
            f"config must be a HistoricalReconciliationRunConfiguration instance, got {target_type}"
        )

    source_path = Path(path)
    rows_with_line_num = _read_schedule_rows(source_path)

    requests: list[HistoricalReconciliationRequest] = []
    for line_num, row in rows_with_line_num:
        request = _parse_schedule_row(row, line_num, source_path, config)
        requests.append(request)

    return requests


def _read_schedule_rows(source_path: Path) -> list[tuple[int, dict[str, str]]]:
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


def _parse_schedule_row(
    row: dict[str, str],
    line_number: int,
    source_path: Path,
    config: HistoricalReconciliationRunConfiguration,
) -> HistoricalReconciliationRequest:
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
        policy = AlignmentPolicy(
            fund_base_currency=config.fund_base_currency,
            required_price_adjustment=config.required_price_adjustment,
            pricing_as_of_date=pricing_as_of,
            minimum_observations=config.minimum_observations,
            max_staleness_calendar_days=config.max_staleness_calendar_days,
        )
        alignment_req = PointInTimeAlignmentRequest(
            fund_id=config.fund_id,
            prediction_timestamp=prediction_ts,
            holdings_source_id=config.holdings_source_id,
            security_price_source_id=config.security_price_source_id,
            policy=policy,
        )
        return HistoricalReconciliationRequest(
            alignment_request=alignment_req,
            period=period,
            fund_price_source_id=config.fund_price_source_id,
        )
    except (
        ValueError,
        PointInTimeAlignmentError,
        HistoricalReconciliationDatasetError,
    ) as error:
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
