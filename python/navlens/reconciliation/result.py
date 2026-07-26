"""Provenance result for point-in-time fund-return reconciliation."""

from dataclasses import dataclass

from navlens import FundReturnReconciliationResult
from navlens.alignment import PointInTimeReturnContributionResult
from navlens.datasets import FundUnitPriceSnapshot


@dataclass(frozen=True, slots=True)
class PointInTimeFundReturnReconciliationResult:
    """Native reconciliation together with every selected point-in-time input."""

    contribution: PointInTimeReturnContributionResult
    start_snapshot: FundUnitPriceSnapshot
    end_snapshot: FundUnitPriceSnapshot
    reconciliation_result: FundReturnReconciliationResult
    fund_price_source_id: str
