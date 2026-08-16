"""Private execution core for historical FX-aware reconciliation datasets."""

from collections.abc import Callable, Iterable
from typing import TypeAlias

from navlens.alignment import (
    PointInTimeAlignmentResult,
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


def _execute_historical_fx_reconciliation(
    requests: Iterable[HistoricalFxReconciliationRequest],
    fx_rate_snapshots: Iterable[FxRateSnapshot],
    fund_price_snapshots: Iterable[FundUnitPriceSnapshot],
    alignment_resolver: _HistoricalFxAlignmentResolver,
) -> HistoricalFxReconciliationDataset:
    """Execute the canonical historical FX-aware reconciliation loop."""
    materialized_requests = tuple(requests)
    fx_rates = tuple(fx_rate_snapshots)
    fund_prices = tuple(fund_price_snapshots)

    validate_chronological_periods(tuple(req.period for req in materialized_requests))

    outcomes: list[HistoricalFxReconciliationOutcome] = [
        _reconcile_single_fx_request(req, fx_rates, fund_prices, alignment_resolver)
        for req in materialized_requests
    ]
    return HistoricalFxReconciliationDataset(outcomes=tuple(outcomes))


def _reconcile_single_fx_request(
    request: HistoricalFxReconciliationRequest,
    fx_rates: tuple[FxRateSnapshot, ...],
    fund_prices: tuple[FundUnitPriceSnapshot, ...],
    alignment_resolver: _HistoricalFxAlignmentResolver,
) -> HistoricalFxReconciliationOutcome:
    try:
        alignment = alignment_resolver(request)
        fx_req = PointInTimeFxReturnContributionRequest(
            alignment_result=alignment,
            target_period=request.period,
            fx_source_id=request.fx_source_id,
            fx_policy=request.fx_policy,
        )
        contribution = calculate_point_in_time_fx_adjusted_return_contribution(fx_req, fx_rates)
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
