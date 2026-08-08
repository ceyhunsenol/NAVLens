"""Point-in-time holdings and security price alignment package."""

from .errors import (
    InvalidPointInTimeAlignmentRequestError,
    InvalidPointInTimeFxReturnContributionRequestError,
    MissingHoldingsSnapshotError,
    PointInTimeAlignmentError,
)
from .fx_orchestration import calculate_point_in_time_fx_adjusted_return_contribution
from .fx_request import PointInTimeFxReturnContributionRequest
from .fx_result import PointInTimeFxAdjustedReturnContributionResult
from .point_in_time import align_point_in_time
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
    "MissingHoldingsSnapshotError",
    "PointInTimeAlignmentError",
    "PointInTimeAlignmentRequest",
    "PointInTimeAlignmentResult",
    "PointInTimeFxAdjustedReturnContributionResult",
    "PointInTimeFxReturnContributionRequest",
    "PointInTimeReturnContributionResult",
    "align_point_in_time",
    "calculate_point_in_time_fx_adjusted_return_contribution",
    "calculate_point_in_time_return_contribution",
    "format_return_contribution_result",
]
