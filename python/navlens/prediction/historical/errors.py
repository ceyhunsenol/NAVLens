"""Boundary exceptions for historical prediction datasets and evaluation."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .request import HistoricalPredictionRequest


class HistoricalPredictionDatasetError(Exception):
    """Base exception for historical prediction dataset errors."""


class InvalidHistoricalPredictionScopeError(HistoricalPredictionDatasetError):
    """Raised when a historical prediction evaluation scope violates contract invariants."""


class InvalidHistoricalPredictionRequestError(HistoricalPredictionDatasetError):
    """Raised when a historical prediction request violates contract invariants."""


class InvalidHistoricalPredictionOutcomeError(HistoricalPredictionDatasetError):
    """Raised when a historical prediction outcome record violates contract invariants."""


class InvalidHistoricalPredictionDatasetError(HistoricalPredictionDatasetError):
    """Raised when a historical prediction dataset violates contract invariants."""


class DuplicateHistoricalPredictionScheduleError(HistoricalPredictionDatasetError):
    """Raised when a prediction schedule contains duplicate target dates or periods."""


class DecreasingHistoricalPredictionScheduleError(HistoricalPredictionDatasetError):
    """Raised when a prediction schedule is not provided in valid chronological order."""


class MixedHistoricalPredictionScopeError(HistoricalPredictionDatasetError):
    """Raised when an outcome or record violates dataset scope or model metadata homogeneity."""

    field_name: str
    expected: str | int | float | None
    actual: str | int | float | None
    request: "HistoricalPredictionRequest | None"

    def __init__(
        self,
        field_name: str,
        expected: str | int | float | None,
        actual: str | int | float | None,
        request: "HistoricalPredictionRequest | None" = None,
    ) -> None:
        self.field_name = field_name
        self.expected = expected
        self.actual = actual
        self.request = request

        req_text = f" for request target {request.target_date}" if request is not None else ""
        expected_text = "<none>" if expected is None else str(expected)
        actual_text = "<none>" if actual is None else str(actual)
        message = (
            f"Mixed prediction scope for field '{field_name}': "
            f"expected {expected_text}, got {actual_text}{req_text}"
        )
        super().__init__(message)


class MissingHistoricalPredictionStartObservationError(HistoricalPredictionDatasetError):
    """Raised when evaluation-time exact start snapshot selection returns nothing."""


class UnexpectedHistoricalPredictionReturnCardinalityError(HistoricalPredictionDatasetError):
    """Raised when native return calculation produces an unexpected number of period returns."""


class InvalidHistoricalPredictionEvaluationError(HistoricalPredictionDatasetError):
    """Raised when a historical prediction evaluation violates contract invariants."""


class InvalidHistoricalPredictionRunResultError(HistoricalPredictionDatasetError):
    """Raised when a historical prediction run result is internally inconsistent."""


class UnsupportedHistoricalPredictionDatasetError(HistoricalPredictionDatasetError):
    """Raised when a dataset type is unsupported for historical prediction evaluation."""


class UnknownHistoricalPredictionOutcomeError(HistoricalPredictionDatasetError):
    """Raised when a dataset outcome type is unrecognized during evaluation."""


class UnknownHistoricalPredictionSkipReasonError(HistoricalPredictionDatasetError):
    """Raised when a dataset skip reason type is unrecognized during evaluation."""
