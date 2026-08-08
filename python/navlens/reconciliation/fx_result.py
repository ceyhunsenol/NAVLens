"""Provenance result for point-in-time FX-aware fund-return reconciliation."""

from dataclasses import dataclass

from navlens import FundReturnReconciliationResult
from navlens.alignment import PointInTimeFxAdjustedReturnContributionResult
from navlens.datasets import FundUnitPriceSnapshot


@dataclass(frozen=True, slots=True)
class PointInTimeFxFundReturnReconciliationResult:
    """FX-aware native reconciliation together with every selected point-in-time input."""

    contribution: PointInTimeFxAdjustedReturnContributionResult
    start_snapshot: FundUnitPriceSnapshot
    end_snapshot: FundUnitPriceSnapshot
    reconciliation_result: FundReturnReconciliationResult
    fund_price_source_id: str
