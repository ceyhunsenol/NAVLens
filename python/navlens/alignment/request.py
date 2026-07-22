"""Request contract for point-in-time alignment."""

from dataclasses import dataclass
from datetime import datetime

from navlens import AlignmentPolicy
from navlens.datasets._timestamps import validate_utc_timestamp

from .errors import InvalidPointInTimeAlignmentRequestError


@dataclass(frozen=True, slots=True)
class PointInTimeAlignmentRequest:
    """Inputs required for point-in-time holdings/security-price alignment."""

    fund_id: str
    prediction_timestamp: datetime
    holdings_source_id: str
    security_price_source_id: str
    policy: AlignmentPolicy

    def __post_init__(self) -> None:
        if not isinstance(self.fund_id, str) or not self.fund_id.strip():
            raise InvalidPointInTimeAlignmentRequestError(
                f"fund_id must be a non-empty string; got {self.fund_id!r}"
            )
        if not isinstance(self.holdings_source_id, str) or not self.holdings_source_id.strip():
            raise InvalidPointInTimeAlignmentRequestError(
                f"holdings_source_id must be a non-empty string; got {self.holdings_source_id!r}"
            )
        if (
            not isinstance(self.security_price_source_id, str)
            or not self.security_price_source_id.strip()
        ):
            raise InvalidPointInTimeAlignmentRequestError(
                "security_price_source_id must be a non-empty string; "
                f"got {self.security_price_source_id!r}"
            )
        if not isinstance(self.policy, AlignmentPolicy):
            raise InvalidPointInTimeAlignmentRequestError(
                f"policy must be an AlignmentPolicy instance; got {type(self.policy).__name__}"
            )

        validate_utc_timestamp(
            self.prediction_timestamp,
            "prediction_timestamp",
            InvalidPointInTimeAlignmentRequestError,
        )
