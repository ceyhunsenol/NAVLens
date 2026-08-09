"""Parsing of provider-neutral historical FX-aware reconciliation schedule CSV files."""

from dataclasses import dataclass
from pathlib import Path

from navlens import (
    AlignmentPolicy,
    FxRateKind,
    FxReturnPolicy,
    PriceCurrencyPolicy,
)
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
from .fx_request import HistoricalFxReconciliationRequest
from .schedule_csv import HistoricalReconciliationRunConfiguration


@dataclass(frozen=True, slots=True)
class HistoricalFxReconciliationRunConfiguration:
    """Static financial policy and source configuration for historical FX reconciliation."""

    base: HistoricalReconciliationRunConfiguration
    fx_source_id: str
    required_fx_rate_kind: FxRateKind
    max_fx_staleness_calendar_days: int

    def __post_init__(self) -> None:
        """Validate type and parameter invariants upon construction."""
        if not isinstance(self.base, HistoricalReconciliationRunConfiguration):
            raise TypeError(
                "base must be a HistoricalReconciliationRunConfiguration instance, "
                f"got {type(self.base).__name__}"
            )
        if not isinstance(self.fx_source_id, str) or not self.fx_source_id.strip():
            raise InvalidHistoricalReconciliationRunConfigurationError(
                f"fx_source_id must be a non-empty string, got {self.fx_source_id!r}"
            )
        if not isinstance(self.required_fx_rate_kind, FxRateKind):
            raise TypeError(
                "required_fx_rate_kind must be an FxRateKind instance, "
                f"got {type(self.required_fx_rate_kind).__name__}"
            )
        if isinstance(self.max_fx_staleness_calendar_days, bool) or not isinstance(
            self.max_fx_staleness_calendar_days, int
        ):
            raise TypeError(
                "max_fx_staleness_calendar_days must be a non-bool integer, "
                f"got {self.max_fx_staleness_calendar_days!r}"
            )
        if self.max_fx_staleness_calendar_days < 0:
            raise InvalidHistoricalReconciliationRunConfigurationError(
                "max_fx_staleness_calendar_days must be non-negative, "
                f"got {self.max_fx_staleness_calendar_days}"
            )


def read_historical_fx_reconciliation_requests_csv(
    path: str | Path,
    config: HistoricalFxReconciliationRunConfiguration,
) -> list[HistoricalFxReconciliationRequest]:
    """Parse a historical schedule CSV into HistoricalFxReconciliationRequest instances."""
    if not isinstance(config, HistoricalFxReconciliationRunConfiguration):
        target_type = type(config).__name__
        raise TypeError(
            "config must be a HistoricalFxReconciliationRunConfiguration instance, "
            f"got {target_type}"
        )

    source_path = Path(path)
    entries = read_schedule_csv_entries(source_path)

    fx_policy = FxReturnPolicy(
        config.required_fx_rate_kind,
        config.max_fx_staleness_calendar_days,
    )

    requests: list[HistoricalFxReconciliationRequest] = []
    for entry in entries:
        try:
            base_policy = AlignmentPolicy(
                fund_base_currency=config.base.fund_base_currency,
                required_price_adjustment=config.base.required_price_adjustment,
                pricing_as_of_date=entry.pricing_as_of_date,
                minimum_observations=config.base.minimum_observations,
                max_staleness_calendar_days=config.base.max_staleness_calendar_days,
            )
            permit_foreign_policy = base_policy.with_price_currency_policy(
                PriceCurrencyPolicy("permit_foreign")
            )
            alignment_req = PointInTimeAlignmentRequest(
                fund_id=config.base.fund_id,
                prediction_timestamp=entry.prediction_timestamp,
                holdings_source_id=config.base.holdings_source_id,
                security_price_source_id=config.base.security_price_source_id,
                policy=permit_foreign_policy,
            )
            fx_req = HistoricalFxReconciliationRequest(
                alignment_request=alignment_req,
                period=entry.period,
                fx_source_id=config.fx_source_id,
                fx_policy=fx_policy,
                fund_price_source_id=config.base.fund_price_source_id,
            )
            requests.append(fx_req)
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
