"""Point-in-time fund-return reconciliation orchestration."""

from collections.abc import Iterable
from datetime import datetime

from navlens import (
    MarketDate,
    calculate_price_period_returns,
    reconcile_fund_return,
)
from navlens.alignment import PointInTimeReturnContributionResult
from navlens.datasets import (
    FundUnitPriceSnapshot,
    select_fund_unit_price_snapshots,
)

from .errors import (
    InvalidFundPriceSourceError,
    MissingExactFundUnitPriceSnapshotError,
    UnexpectedNativeReturnCardinalityError,
)
from .result import PointInTimeFundReturnReconciliationResult


def reconcile_point_in_time_fund_return(
    contribution: PointInTimeReturnContributionResult,
    fund_price_snapshots: Iterable[FundUnitPriceSnapshot],
    *,
    fund_price_source_id: str,
) -> PointInTimeFundReturnReconciliationResult:
    """Reconcile exact published fund return with an aligned portfolio contribution."""
    if not isinstance(fund_price_source_id, str) or not fund_price_source_id.strip():
        raise InvalidFundPriceSourceError(fund_price_source_id)

    alignment_request = contribution.alignment_result.request
    fund_id = alignment_request.fund_id
    prediction_timestamp = alignment_request.prediction_timestamp
    period = contribution.contribution_result.period

    selected = select_fund_unit_price_snapshots(
        fund_price_snapshots,
        source_id=fund_price_source_id,
        fund_id=fund_id,
        at_timestamp=prediction_timestamp,
        pricing_as_of_date=period.period_end_date,
    )
    start_snapshot = _require_exact_snapshot(
        selected,
        period.period_start_date,
        fund_id,
        fund_price_source_id,
        prediction_timestamp,
    )
    end_snapshot = _require_exact_snapshot(
        selected,
        period.period_end_date,
        fund_id,
        fund_price_source_id,
        prediction_timestamp,
    )

    period_returns = calculate_price_period_returns(
        fund_id,
        [start_snapshot.observation, end_snapshot.observation],
    )
    if len(period_returns) != 1:
        raise UnexpectedNativeReturnCardinalityError(len(period_returns))

    reconciliation_result = reconcile_fund_return(
        period_returns[0],
        contribution.contribution_result,
    )
    return PointInTimeFundReturnReconciliationResult(
        contribution=contribution,
        start_snapshot=start_snapshot,
        end_snapshot=end_snapshot,
        reconciliation_result=reconciliation_result,
        fund_price_source_id=fund_price_source_id,
    )


def _require_exact_snapshot(
    snapshots: tuple[FundUnitPriceSnapshot, ...],
    required_date: MarketDate,
    fund_id: str,
    source_id: str,
    prediction_timestamp: datetime,
) -> FundUnitPriceSnapshot:
    for snapshot in snapshots:
        if snapshot.observation.date == required_date:
            return snapshot
    raise MissingExactFundUnitPriceSnapshotError(
        fund_id,
        source_id,
        required_date,
        prediction_timestamp,
    )
