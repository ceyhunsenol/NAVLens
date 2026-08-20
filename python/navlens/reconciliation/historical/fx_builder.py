"""Orchestrator for building a chronological historical FX-aware reconciliation dataset."""

from collections.abc import Iterable

from navlens.alignment import align_point_in_time
from navlens.datasets import (
    FundUnitPriceSnapshot,
    FxRateSnapshot,
    HoldingSnapshot,
    SecurityPriceSnapshot,
)

from ._fx_builder_core import (
    _execute_historical_fx_reconciliation,
    calculate_fx_contribution_from_snapshots,
)
from .fx_dataset import HistoricalFxReconciliationDataset
from .fx_request import HistoricalFxReconciliationRequest


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

    return _execute_historical_fx_reconciliation(
        requests=materialized_requests,
        fund_price_snapshots=fund_prices,
        alignment_resolver=lambda req: align_point_in_time(
            req.alignment_request,
            holdings,
            security_prices,
        ),
        contribution_resolver=lambda req, alignment: calculate_fx_contribution_from_snapshots(
            req,
            alignment,
            fx_rates,
        ),
    )
