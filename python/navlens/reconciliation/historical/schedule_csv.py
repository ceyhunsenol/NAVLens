"""Parsing of provider-neutral historical reconciliation schedule CSV files."""

from dataclasses import dataclass
from pathlib import Path

from navlens import AlignmentPolicy, CurrencyCode, PriceAdjustment
from navlens.alignment import PointInTimeAlignmentRequest
from navlens.alignment.errors import PointInTimeAlignmentError

from ._schedule_csv_entry import (
    CsvHistoricalScheduleSourceError,
    read_schedule_csv_entries,
)
from .errors import (
    HistoricalReconciliationDatasetError,
    InvalidHistoricalReconciliationRunConfigurationError,
)
from .request import HistoricalReconciliationRequest


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
    entries = read_schedule_csv_entries(source_path)

    requests: list[HistoricalReconciliationRequest] = []
    for entry in entries:
        try:
            policy = AlignmentPolicy(
                fund_base_currency=config.fund_base_currency,
                required_price_adjustment=config.required_price_adjustment,
                pricing_as_of_date=entry.pricing_as_of_date,
                minimum_observations=config.minimum_observations,
                max_staleness_calendar_days=config.max_staleness_calendar_days,
            )
            alignment_req = PointInTimeAlignmentRequest(
                fund_id=config.fund_id,
                prediction_timestamp=entry.prediction_timestamp,
                holdings_source_id=config.holdings_source_id,
                security_price_source_id=config.security_price_source_id,
                policy=policy,
            )
            req = HistoricalReconciliationRequest(
                alignment_request=alignment_req,
                period=entry.period,
                fund_price_source_id=config.fund_price_source_id,
            )
            requests.append(req)
        except (
            ValueError,
            PointInTimeAlignmentError,
            HistoricalReconciliationDatasetError,
        ) as error:
            if isinstance(error, CsvHistoricalScheduleSourceError):
                raise
            line_no = entry.physical_line_number
            raise CsvHistoricalScheduleSourceError(
                f"cannot parse schedule CSV {source_path} at row {line_no}: {error}"
            ) from error

    return requests
