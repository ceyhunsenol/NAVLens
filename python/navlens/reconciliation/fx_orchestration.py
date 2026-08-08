"""Point-in-time FX-aware fund-return reconciliation orchestration."""

from collections.abc import Iterable

from navlens import reconcile_fx_adjusted_fund_return
from navlens.alignment import PointInTimeFxAdjustedReturnContributionResult
from navlens.datasets import FundUnitPriceSnapshot

from ._snapshots import select_exact_period_fund_return
from .fx_result import PointInTimeFxFundReturnReconciliationResult


def reconcile_point_in_time_fx_adjusted_fund_return(
    contribution: PointInTimeFxAdjustedReturnContributionResult,
    fund_price_snapshots: Iterable[FundUnitPriceSnapshot],
    *,
    fund_price_source_id: str,
) -> PointInTimeFxFundReturnReconciliationResult:
    """Reconcile exact published fund return with an aligned FX-aware portfolio contribution."""
    alignment_request = contribution.request.alignment_result.request
    fund_id = alignment_request.fund_id
    prediction_timestamp = alignment_request.prediction_timestamp
    period = contribution.contribution_result.period

    start_snapshot, end_snapshot, published_return = select_exact_period_fund_return(
        fund_price_snapshots,
        fund_id=fund_id,
        fund_price_source_id=fund_price_source_id,
        prediction_timestamp=prediction_timestamp,
        period=period,
    )

    reconciliation_result = reconcile_fx_adjusted_fund_return(
        published_return,
        contribution.contribution_result,
    )
    return PointInTimeFxFundReturnReconciliationResult(
        contribution=contribution,
        start_snapshot=start_snapshot,
        end_snapshot=end_snapshot,
        reconciliation_result=reconciliation_result,
        fund_price_source_id=fund_price_source_id,
    )
