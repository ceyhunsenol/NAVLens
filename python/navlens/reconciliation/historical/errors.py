"""Boundary exceptions for historical reconciliation datasets and evaluation."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navlens import ReturnPeriod


class HistoricalReconciliationDatasetError(Exception):
    """Base exception for historical reconciliation dataset errors."""


class InvalidHistoricalReconciliationRunConfigurationError(ValueError):
    """Raised when a historical reconciliation run configuration has an invalid value."""


class InvalidHistoricalReconciliationRequestError(HistoricalReconciliationDatasetError):
    """Raised when a historical reconciliation request has an invalid field."""


class DuplicatePeriodError(HistoricalReconciliationDatasetError):
    """Raised when a period is identical to a preceding period."""


class DecreasingPeriodError(HistoricalReconciliationDatasetError):
    """Raised when periods are not provided in strictly ascending order."""


class InvalidHistoricalReconciliationEvaluationError(HistoricalReconciliationDatasetError):
    """Raised when a historical reconciliation evaluation result violates contract invariants."""


class InvalidHistoricalReconciliationEvaluationScopeError(HistoricalReconciliationDatasetError):
    """Raised when a historical reconciliation evaluation scope violates contract invariants."""


class UnknownOutcomeError(HistoricalReconciliationDatasetError):
    """Raised when a historical dataset outcome record type is unsupported."""


class UnknownSkipReasonError(HistoricalReconciliationDatasetError):
    """Raised when a historical skipped reconciliation record has an unsupported skip reason."""


class UnsupportedHistoricalReconciliationDatasetError(HistoricalReconciliationDatasetError):
    """Raised when historical evaluation receives an unsupported dataset type."""


class MixedHistoricalReconciliationScopeError(HistoricalReconciliationDatasetError):
    """Raised when an evaluated dataset contains outcomes with mismatched scope fields."""

    field_name: str
    expected: str | None
    actual: str | None
    period: "ReturnPeriod | None"

    def __init__(
        self,
        field_name: str,
        expected: str | None,
        actual: str | None,
        period: "ReturnPeriod | None" = None,
    ) -> None:
        self.field_name = field_name
        self.expected = expected
        self.actual = actual
        self.period = period

        period_text = (
            f" for period {period.period_start_date} -> {period.period_end_date}"
            if period is not None
            else ""
        )
        expected_text = "<none>" if expected is None else expected
        actual_text = "<none>" if actual is None else actual
        message = (
            f"Mixed reconciliation scope for field '{field_name}': "
            f"expected {expected_text}, got {actual_text}{period_text}"
        )
        super().__init__(message)
