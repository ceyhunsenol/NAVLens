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


class PredictionArtifactError(ValueError):
    """Base error for stored prediction artifact loading and evaluation."""


class InvalidPredictionArtifactError(PredictionArtifactError):
    """Raised when a stored prediction artifact violates its versioned schema."""


class UnsupportedPredictionArtifactSourceError(PredictionArtifactError):
    """Raised when an evaluator cannot acquire the artifact's declared source."""


class MissingRealizedPriceObservationError(PredictionArtifactError):
    """Raised when an exact realized period-boundary price is unavailable."""


class UnexpectedRealizedReturnCardinalityError(PredictionArtifactError):
    """Raised when two exact prices do not produce one native period return."""
