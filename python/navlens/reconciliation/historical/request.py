"""Immutable request contract for historical reconciliation datasets."""

from dataclasses import dataclass

from navlens import ReturnPeriod
from navlens.alignment import PointInTimeAlignmentRequest

from .errors import InvalidHistoricalReconciliationRequestError


@dataclass(frozen=True, slots=True)
class HistoricalReconciliationRequest:
    """A single-period request boundary for the dataset orchestrator."""

    alignment_request: PointInTimeAlignmentRequest
    period: ReturnPeriod
    fund_price_source_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.alignment_request, PointInTimeAlignmentRequest):
            raise InvalidHistoricalReconciliationRequestError(
                "alignment_request must be a PointInTimeAlignmentRequest instance; "
                f"got {type(self.alignment_request).__name__}"
            )
        if not isinstance(self.period, ReturnPeriod):
            raise InvalidHistoricalReconciliationRequestError(
                f"period must be a ReturnPeriod instance; got {type(self.period).__name__}"
            )
        if not isinstance(self.fund_price_source_id, str) or not self.fund_price_source_id.strip():
            raise InvalidHistoricalReconciliationRequestError(
                "fund_price_source_id must be a non-empty string; "
                f"got {self.fund_price_source_id!r}"
            )
