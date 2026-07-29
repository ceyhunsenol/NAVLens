"""Orchestrator for building a chronological historical reconciliation dataset."""

from collections.abc import Iterable

from navlens.alignment import align_point_in_time, calculate_point_in_time_return_contribution
from navlens.alignment.errors import MissingHoldingsSnapshotError
from navlens.datasets import FundUnitPriceSnapshot, HoldingSnapshot, SecurityPriceSnapshot

from ..errors import MissingExactFundUnitPriceSnapshotError
from ..orchestration import reconcile_point_in_time_fund_return
from .dataset import HistoricalReconciliationDataset
from .errors import DecreasingPeriodError, DuplicatePeriodError
from .outcome import (
    HistoricalReconciliationOutcome,
    HistoricalReconciliationRecord,
    MissingFundPriceSkip,
    MissingHoldingsSkip,
    SkippedReconciliationRecord,
)
from .request import HistoricalReconciliationRequest


def build_historical_reconciliation_dataset(
    requests: Iterable[HistoricalReconciliationRequest],
    holdings_snapshots: Iterable[HoldingSnapshot],
    security_price_snapshots: Iterable[SecurityPriceSnapshot],
    fund_price_snapshots: Iterable[FundUnitPriceSnapshot],
) -> HistoricalReconciliationDataset:
    """Build a point-in-time dataset by executing the exact canonical orchestration per request."""
    materialized_requests = tuple(requests)
    holdings = tuple(holdings_snapshots)
    security_prices = tuple(security_price_snapshots)
    fund_prices = tuple(fund_price_snapshots)

    _validate_chronological_ordering(materialized_requests)

    outcomes: list[HistoricalReconciliationOutcome] = []
    for req in materialized_requests:
        try:
            alignment = align_point_in_time(req.alignment_request, holdings, security_prices)
            contribution = calculate_point_in_time_return_contribution(alignment, req.period)
            reconciliation = reconcile_point_in_time_fund_return(
                contribution,
                fund_prices,
                fund_price_source_id=req.fund_price_source_id,
            )
            outcomes.append(HistoricalReconciliationRecord(request=req, result=reconciliation))
        except MissingHoldingsSnapshotError:
            outcomes.append(SkippedReconciliationRecord(request=req, reason=MissingHoldingsSkip()))
        except MissingExactFundUnitPriceSnapshotError as exc:
            outcomes.append(
                SkippedReconciliationRecord(
                    request=req, reason=MissingFundPriceSkip(exc.required_date)
                )
            )

    return HistoricalReconciliationDataset(outcomes=tuple(outcomes))


def _validate_chronological_ordering(requests: tuple[HistoricalReconciliationRequest, ...]) -> None:
    seen_periods = []
    prev_end = None
    for req in requests:
        current_period = req.period
        current_end = current_period.period_end_date
        if any(current_period == seen_period for seen_period in seen_periods):
            raise DuplicatePeriodError(f"Duplicate period detected: {current_period}")
        if prev_end is not None and current_end <= prev_end:
            raise DecreasingPeriodError(
                f"Period end dates must be strictly increasing; got {current_end} after {prev_end}"
            )
        seen_periods.append(current_period)
        prev_end = current_end
