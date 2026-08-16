"""Orchestrator for building a chronological source-backed historical reconciliation dataset."""

from collections.abc import Iterable
from datetime import date

from navlens.alignment import align_point_in_time_from_source
from navlens.datasets import FundUnitPriceSnapshot, HoldingSnapshot, SecurityPriceSource

from ._builder_core import _execute_historical_reconciliation
from .dataset import HistoricalReconciliationDataset
from .request import HistoricalReconciliationRequest


def build_historical_reconciliation_dataset_from_source(
    requests: Iterable[HistoricalReconciliationRequest],
    holdings_snapshots: Iterable[HoldingSnapshot],
    security_price_source: SecurityPriceSource,
    fund_price_snapshots: Iterable[FundUnitPriceSnapshot],
    *,
    price_history_start_date: date,
) -> HistoricalReconciliationDataset:
    """Build a point-in-time dataset dynamically using a provider-neutral SecurityPriceSource."""
    materialized_requests = tuple(requests)
    holdings = tuple(holdings_snapshots)
    fund_prices = tuple(fund_price_snapshots)

    return _execute_historical_reconciliation(
        requests=materialized_requests,
        fund_price_snapshots=fund_prices,
        alignment_resolver=lambda req: align_point_in_time_from_source(
            req.alignment_request,
            holdings,
            security_price_source,
            price_history_start_date,
        ),
    )
