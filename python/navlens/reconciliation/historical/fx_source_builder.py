"""Orchestrator for source-backed historical FX-aware reconciliation datasets."""

from collections.abc import Iterable
from datetime import date

from navlens.alignment import (
    align_point_in_time_from_source,
    calculate_point_in_time_fx_adjusted_return_contribution_from_source,
)
from navlens.datasets import (
    FundUnitPriceSnapshot,
    FxRateSnapshot,
    FxRateSource,
    HoldingSnapshot,
    SecurityPriceSource,
)

from ._fx_builder_core import (
    _execute_historical_fx_reconciliation,
    build_fx_contribution_request,
    calculate_fx_contribution_from_snapshots,
)
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
        fund_price_snapshots=fund_prices,
        alignment_resolver=lambda req: align_point_in_time_from_source(
            req.alignment_request,
            holdings,
            security_price_source,
            price_history_start_date,
        ),
        contribution_resolver=lambda req, alignment: calculate_fx_contribution_from_snapshots(
            req,
            alignment,
            fx_rates,
        ),
    )


def build_historical_fx_reconciliation_dataset_from_sources(
    requests: Iterable[HistoricalFxReconciliationRequest],
    holdings_snapshots: Iterable[HoldingSnapshot],
    security_price_source: SecurityPriceSource,
    fx_rate_source: FxRateSource,
    fund_price_snapshots: Iterable[FundUnitPriceSnapshot],
    *,
    price_history_start_date: date,
) -> HistoricalFxReconciliationDataset:
    """Build an FX-aware dataset using provider-neutral security-price and FX sources."""
    materialized_requests = tuple(requests)
    holdings = tuple(holdings_snapshots)
    fund_prices = tuple(fund_price_snapshots)

    return _execute_historical_fx_reconciliation(
        requests=materialized_requests,
        fund_price_snapshots=fund_prices,
        alignment_resolver=lambda req: align_point_in_time_from_source(
            req.alignment_request,
            holdings,
            security_price_source,
            price_history_start_date,
        ),
        contribution_resolver=lambda req, alignment: (
            calculate_point_in_time_fx_adjusted_return_contribution_from_source(
                build_fx_contribution_request(req, alignment),
                fx_rate_source,
            )
        ),
    )
