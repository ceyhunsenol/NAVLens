"""Private execution core for historical reconciliation datasets."""

from collections.abc import Callable, Iterable
from typing import TypeAlias

from navlens.alignment import (
    PointInTimeAlignmentResult,
    calculate_point_in_time_return_contribution,
)
from navlens.alignment.errors import MissingHoldingsSnapshotError
from navlens.datasets import FundUnitPriceSnapshot

from ..errors import MissingExactFundUnitPriceSnapshotError
from ..orchestration import reconcile_point_in_time_fund_return
from ._ordering import validate_chronological_periods
from .dataset import HistoricalReconciliationDataset
from .outcome import (
    HistoricalReconciliationOutcome,
    HistoricalReconciliationRecord,
    MissingFundPriceSkip,
    MissingHoldingsSkip,
    SkippedReconciliationRecord,
)
from .request import HistoricalReconciliationRequest

_HistoricalAlignmentResolver: TypeAlias = Callable[
    [HistoricalReconciliationRequest], PointInTimeAlignmentResult
]


def _execute_historical_reconciliation(
    requests: Iterable[HistoricalReconciliationRequest],
    fund_price_snapshots: Iterable[FundUnitPriceSnapshot],
    alignment_resolver: _HistoricalAlignmentResolver,
) -> HistoricalReconciliationDataset:
    """Execute the canonical historical reconciliation loop for any alignment resolver."""
    materialized_requests = tuple(requests)
    fund_prices = tuple(fund_price_snapshots)

    validate_chronological_periods(tuple(req.period for req in materialized_requests))

    outcomes: list[HistoricalReconciliationOutcome] = []
    for req in materialized_requests:
        try:
            alignment = alignment_resolver(req)
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
