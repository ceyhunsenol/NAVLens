"""Orchestrator for building a chronological historical FX-aware reconciliation dataset."""

from collections.abc import Iterable

from navlens.alignment import (
    PointInTimeFxReturnContributionRequest,
    align_point_in_time,
    calculate_point_in_time_fx_adjusted_return_contribution,
)
from navlens.alignment.errors import MissingHoldingsSnapshotError
from navlens.datasets import (
    FundUnitPriceSnapshot,
    FxRateSnapshot,
    HoldingSnapshot,
    SecurityPriceSnapshot,
)

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


def build_historical_fx_reconciliation_dataset(
    requests: Iterable[HistoricalFxReconciliationRequest],
    holdings_snapshots: Iterable[HoldingSnapshot],
    security_price_snapshots: Iterable[SecurityPriceSnapshot],
    fx_rate_snapshots: Iterable[FxRateSnapshot],
    fund_price_snapshots: Iterable[FundUnitPriceSnapshot],
) -> HistoricalFxReconciliationDataset:
    """Build a point-in-time FX-aware dataset by executing canonical orchestration per request."""
    materialized_requests = tuple(requests)
    holdings = tuple(holdings_snapshots)
    security_prices = tuple(security_price_snapshots)
    fx_rates = tuple(fx_rate_snapshots)
    fund_prices = tuple(fund_price_snapshots)

    validate_chronological_periods(tuple(req.period for req in materialized_requests))

    outcomes: list[HistoricalFxReconciliationOutcome] = []
    for req in materialized_requests:
        try:
            alignment = align_point_in_time(req.alignment_request, holdings, security_prices)
            fx_req = PointInTimeFxReturnContributionRequest(
                alignment_result=alignment,
                target_period=req.period,
                fx_source_id=req.fx_source_id,
                fx_policy=req.fx_policy,
            )
            contribution = calculate_point_in_time_fx_adjusted_return_contribution(fx_req, fx_rates)
            reconciliation = reconcile_point_in_time_fx_adjusted_fund_return(
                contribution,
                fund_prices,
                fund_price_source_id=req.fund_price_source_id,
            )
            outcomes.append(HistoricalFxReconciliationRecord(request=req, result=reconciliation))
        except MissingHoldingsSnapshotError:
            outcomes.append(
                SkippedFxReconciliationRecord(request=req, reason=MissingHoldingsSkip())
            )
        except MissingExactFundUnitPriceSnapshotError as exc:
            outcomes.append(
                SkippedFxReconciliationRecord(
                    request=req, reason=MissingFundPriceSkip(exc.required_date)
                )
            )

    return HistoricalFxReconciliationDataset(outcomes=tuple(outcomes))
