"""Orchestrator for source-backed historical FX-aware reconciliation datasets."""

from collections.abc import Iterable
from datetime import date

from navlens.alignment import align_point_in_time_from_source
from navlens.datasets import (
    FundUnitPriceSnapshot,
    FxRateSnapshot,
    HoldingSnapshot,
    SecurityPriceSource,
)

from ._fx_builder_core import _execute_historical_fx_reconciliation
from .fx_dataset import HistoricalFxReconciliationDataset
from .fx_request import HistoricalFxReconciliationRequest


def build_historical_fx_reconciliation_dataset_from_security_price_source(
    requests: Iterable[HistoricalFxReconciliationRequest],
    holdings_snapshots: Iterable[HoldingSnapshot],
    security_price_source: SecurityPriceSource,
    fx_rate_snapshots: Iterable[FxRateSnapshot],
    fund_price_snapshots: Iterable[FundUnitPriceSnapshot],
    *,
    price_history_start_date: date,
) -> HistoricalFxReconciliationDataset:
    """Build a point-in-time FX dataset dynamically using a provider-neutral SecurityPriceSource."""
    materialized_requests = tuple(requests)
    holdings = tuple(holdings_snapshots)
    fx_rates = tuple(fx_rate_snapshots)
    fund_prices = tuple(fund_price_snapshots)

    return _execute_historical_fx_reconciliation(
        requests=materialized_requests,
        fx_rate_snapshots=fx_rates,
        fund_price_snapshots=fund_prices,
        alignment_resolver=lambda req: align_point_in_time_from_source(
            req.alignment_request,
            holdings,
            security_price_source,
            price_history_start_date,
        ),
    )
