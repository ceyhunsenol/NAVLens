"""Private execution core for historical FX-aware reconciliation datasets."""

from collections.abc import Callable, Iterable
from typing import TypeAlias

from navlens.alignment import (
    PointInTimeAlignmentResult,
    PointInTimeFxAdjustedReturnContributionResult,
    PointInTimeFxReturnContributionRequest,
    calculate_point_in_time_fx_adjusted_return_contribution,
)
from navlens.alignment.errors import MissingHoldingsSnapshotError
from navlens.datasets import FundUnitPriceSnapshot, FxRateSnapshot

from ..errors import MissingExactFundUnitPriceSnapshotError
from ..fx_orchestration import reconcile_point_in_time_fx_adjusted_fund_return
from ._ordering import validate_chronological_periods
from .fx_dataset import HistoricalFxReconciliationDataset
from .fx_outcome import (
    HistoricalFxReconciliationOutcome,
    HistoricalFxReconciliationRecord,
    SkippedFxReconciliationRecord,
)
from .fx_request import HistoricalFxReconciliationRequest
from .outcome import MissingFundPriceSkip, MissingHoldingsSkip

_HistoricalFxAlignmentResolver: TypeAlias = Callable[
    [HistoricalFxReconciliationRequest], PointInTimeAlignmentResult
]
_HistoricalFxContributionResolver: TypeAlias = Callable[
    [HistoricalFxReconciliationRequest, PointInTimeAlignmentResult],
    PointInTimeFxAdjustedReturnContributionResult,
]


def _execute_historical_fx_reconciliation(
    requests: Iterable[HistoricalFxReconciliationRequest],
    fund_price_snapshots: Iterable[FundUnitPriceSnapshot],
    alignment_resolver: _HistoricalFxAlignmentResolver,
    contribution_resolver: _HistoricalFxContributionResolver,
) -> HistoricalFxReconciliationDataset:
    """Execute the canonical historical FX-aware reconciliation loop."""
    materialized_requests = tuple(requests)
    fund_prices = tuple(fund_price_snapshots)

    validate_chronological_periods(tuple(req.period for req in materialized_requests))

    outcomes: list[HistoricalFxReconciliationOutcome] = [
        _reconcile_single_fx_request(
            req,
            fund_prices,
            alignment_resolver,
            contribution_resolver,
        )
        for req in materialized_requests
    ]
    return HistoricalFxReconciliationDataset(outcomes=tuple(outcomes))


def _reconcile_single_fx_request(
    request: HistoricalFxReconciliationRequest,
    fund_prices: tuple[FundUnitPriceSnapshot, ...],
    alignment_resolver: _HistoricalFxAlignmentResolver,
    contribution_resolver: _HistoricalFxContributionResolver,
) -> HistoricalFxReconciliationOutcome:
    try:
        alignment = alignment_resolver(request)
        contribution = contribution_resolver(request, alignment)
        reconciliation = reconcile_point_in_time_fx_adjusted_fund_return(
            contribution,
            fund_prices,
            fund_price_source_id=request.fund_price_source_id,
        )
        return HistoricalFxReconciliationRecord(request=request, result=reconciliation)
    except MissingHoldingsSnapshotError:
        return SkippedFxReconciliationRecord(request=request, reason=MissingHoldingsSkip())
    except MissingExactFundUnitPriceSnapshotError as exc:
        return SkippedFxReconciliationRecord(
            request=request, reason=MissingFundPriceSkip(exc.required_date)
        )


def calculate_fx_contribution_from_snapshots(
    request: HistoricalFxReconciliationRequest,
    alignment: PointInTimeAlignmentResult,
    fx_rates: tuple[FxRateSnapshot, ...],
) -> PointInTimeFxAdjustedReturnContributionResult:
    """Build the per-period request and delegate to canonical snapshot orchestration."""
    fx_request = build_fx_contribution_request(request, alignment)
    return calculate_point_in_time_fx_adjusted_return_contribution(fx_request, fx_rates)


def build_fx_contribution_request(
    request: HistoricalFxReconciliationRequest,
    alignment: PointInTimeAlignmentResult,
) -> PointInTimeFxReturnContributionRequest:
    """Map a historical request and alignment result to the point-in-time contract."""
    return PointInTimeFxReturnContributionRequest(
        alignment_result=alignment,
        target_period=request.period,
        fx_source_id=request.fx_source_id,
        fx_policy=request.fx_policy,
    )
