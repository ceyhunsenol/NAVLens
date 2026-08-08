"""Immutable request contract for historical FX-aware reconciliation datasets."""

from dataclasses import dataclass

from navlens import FxReturnPolicy, PriceCurrencyPolicy, ReturnPeriod
from navlens.alignment import PointInTimeAlignmentRequest

from .errors import InvalidHistoricalReconciliationRequestError


@dataclass(frozen=True, slots=True)
class HistoricalFxReconciliationRequest:
    """A single-period FX-aware request boundary for the dataset orchestrator."""

    alignment_request: PointInTimeAlignmentRequest
    period: ReturnPeriod
    fx_source_id: str
    fx_policy: FxReturnPolicy
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
        if not isinstance(self.fx_source_id, str) or not self.fx_source_id.strip():
            raise InvalidHistoricalReconciliationRequestError(
                f"fx_source_id must be a non-empty string; got {self.fx_source_id!r}"
            )
        if not isinstance(self.fx_policy, FxReturnPolicy):
            raise InvalidHistoricalReconciliationRequestError(
                f"fx_policy must be an FxReturnPolicy instance; got {type(self.fx_policy).__name__}"
            )
        if not isinstance(self.fund_price_source_id, str) or not self.fund_price_source_id.strip():
            raise InvalidHistoricalReconciliationRequestError(
                "fund_price_source_id must be a non-empty string; "
                f"got {self.fund_price_source_id!r}"
            )

        policy = self.alignment_request.policy
        if policy.price_currency_policy != PriceCurrencyPolicy("permit_foreign"):
            raise InvalidHistoricalReconciliationRequestError(
                "alignment policy must permit foreign price currency alignment; "
                f"got price_currency_policy={policy.price_currency_policy.name!r}"
            )
