"""Typed exception hierarchy for point-in-time prediction orchestration."""


class PointInTimePredictionError(ValueError):
    """Base operational exception for point-in-time prediction errors."""


class NoEligibleSnapshotsError(PointInTimePredictionError):
    """Raised when no fund price snapshots meet point-in-time eligibility criteria."""


class InsufficientVisibleHistoryError(PointInTimePredictionError):
    """Raised when the visible historical return count is less than the required minimum."""


class InvalidPredictionWindowError(PointInTimePredictionError):
    """Raised when prediction_date, target_date, or snapshot dates violate sequence rules."""


class InvalidPredictionConfigurationError(PointInTimePredictionError):
    """Raised when model configuration parameters (lookback, minimum history) are invalid."""


class StaleFundUnitPriceHistoryError(PointInTimePredictionError):
    """Raised when the latest visible fund price exceeds the explicit age policy."""
