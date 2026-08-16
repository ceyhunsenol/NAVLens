"""Point-in-time holdings and security price alignment package."""

from .errors import (
    InvalidPointInTimeAlignmentRequestError,
    InvalidPointInTimeFxReturnContributionRequestError,
    InvalidPriceHistoryStartError,
    MissingHoldingsSnapshotError,
    PointInTimeAlignmentError,
    SecurityPriceSourceMismatchError,
)
from .fx_orchestration import calculate_point_in_time_fx_adjusted_return_contribution
from .fx_request import PointInTimeFxReturnContributionRequest
from .fx_result import PointInTimeFxAdjustedReturnContributionResult
from .fx_return_contribution_formatting import format_fx_return_contribution_result
from .point_in_time import align_point_in_time, align_point_in_time_from_source
from .request import PointInTimeAlignmentRequest
from .result import PointInTimeAlignmentResult
from .return_contribution import (
    PointInTimeReturnContributionResult,
    calculate_point_in_time_return_contribution,
)
from .return_contribution_formatting import format_return_contribution_result

__all__ = [
    "InvalidPointInTimeAlignmentRequestError",
    "InvalidPointInTimeFxReturnContributionRequestError",
    "InvalidPriceHistoryStartError",
    "MissingHoldingsSnapshotError",
    "PointInTimeAlignmentError",
    "PointInTimeAlignmentRequest",
    "PointInTimeAlignmentResult",
    "PointInTimeFxAdjustedReturnContributionResult",
    "PointInTimeFxReturnContributionRequest",
    "PointInTimeReturnContributionResult",
    "SecurityPriceSourceMismatchError",
    "align_point_in_time",
    "align_point_in_time_from_source",
    "calculate_point_in_time_fx_adjusted_return_contribution",
    "calculate_point_in_time_return_contribution",
    "format_fx_return_contribution_result",
    "format_return_contribution_result",
]
