"""Domain boundary exceptions for historical dataset construction."""


class HistoricalReconciliationDatasetError(Exception):
    """Base exception for historical reconciliation dataset errors."""


class InvalidHistoricalReconciliationRequestError(HistoricalReconciliationDatasetError):
    """Raised when a historical reconciliation request has an invalid field."""


class DuplicatePeriodError(HistoricalReconciliationDatasetError):
    """Raised when a period is identical to a preceding period."""


class DecreasingPeriodError(HistoricalReconciliationDatasetError):
    """Raised when periods are not provided in strictly ascending order."""
