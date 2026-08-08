"""Request contract for point-in-time FX-aware return contribution orchestration."""

from dataclasses import dataclass

from navlens import FxReturnPolicy, PriceCurrencyPolicy, ReturnPeriod

from .errors import InvalidPointInTimeFxReturnContributionRequestError
from .result import PointInTimeAlignmentResult


@dataclass(frozen=True, slots=True)
class PointInTimeFxReturnContributionRequest:
    """Inputs required for point-in-time FX-aware return contribution orchestration."""

    alignment_result: PointInTimeAlignmentResult
    target_period: ReturnPeriod
    fx_source_id: str
    fx_policy: FxReturnPolicy

    def __post_init__(self) -> None:
        if not isinstance(self.alignment_result, PointInTimeAlignmentResult):
            raise InvalidPointInTimeFxReturnContributionRequestError(
                "alignment_result must be a PointInTimeAlignmentResult instance; "
                f"got {type(self.alignment_result).__name__}"
            )
        if not isinstance(self.target_period, ReturnPeriod):
            raise InvalidPointInTimeFxReturnContributionRequestError(
                "target_period must be a ReturnPeriod instance; "
                f"got {type(self.target_period).__name__}"
            )
        if not isinstance(self.fx_source_id, str) or not self.fx_source_id.strip():
            raise InvalidPointInTimeFxReturnContributionRequestError(
                "fx_source_id must be a non-empty, non-whitespace string; "
                f"got {self.fx_source_id!r}"
            )
        if not isinstance(self.fx_policy, FxReturnPolicy):
            raise InvalidPointInTimeFxReturnContributionRequestError(
                f"fx_policy must be an FxReturnPolicy instance; got {type(self.fx_policy).__name__}"
            )

        policy = self.alignment_result.request.policy
        if policy.price_currency_policy != PriceCurrencyPolicy("permit_foreign"):
            raise InvalidPointInTimeFxReturnContributionRequestError(
                "alignment policy must permit foreign price currency alignment; "
                f"got price_currency_policy={policy.price_currency_policy.name!r}"
            )
