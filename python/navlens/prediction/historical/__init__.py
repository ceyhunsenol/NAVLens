"""Provider-neutral point-in-time historical prediction contracts."""

from .builder import build_historical_prediction_dataset
from .dataset import HistoricalPredictionDataset
from .errors import (
    DecreasingHistoricalPredictionScheduleError,
    DuplicateHistoricalPredictionScheduleError,
    HistoricalPredictionDatasetError,
    InvalidHistoricalPredictionDatasetError,
    InvalidHistoricalPredictionOutcomeError,
    InvalidHistoricalPredictionRequestError,
    InvalidHistoricalPredictionScopeError,
    MissingHistoricalPredictionStartObservationError,
    MixedHistoricalPredictionScopeError,
    UnexpectedHistoricalPredictionReturnCardinalityError,
)
from .outcome import (
    HistoricalPredictionOutcome,
    HistoricalPredictionRecord,
    SkippedPredictionRecord,
)
from .request import HistoricalPredictionRequest
from .scope import HistoricalPredictionEvaluationScope
from .skip_reason import (
    HistoricalPredictionSkipReason,
    InsufficientVisiblePredictionHistorySkip,
    MissingRealizedObservationSkip,
    NoEligiblePredictionSnapshotsSkip,
    TargetObservationNotYetAvailableSkip,
)

__all__ = [
    "DecreasingHistoricalPredictionScheduleError",
    "DuplicateHistoricalPredictionScheduleError",
    "HistoricalPredictionDataset",
    "HistoricalPredictionDatasetError",
    "HistoricalPredictionEvaluationScope",
    "HistoricalPredictionOutcome",
    "HistoricalPredictionRecord",
    "HistoricalPredictionRequest",
    "HistoricalPredictionSkipReason",
    "InsufficientVisiblePredictionHistorySkip",
    "InvalidHistoricalPredictionDatasetError",
    "InvalidHistoricalPredictionOutcomeError",
    "InvalidHistoricalPredictionRequestError",
    "InvalidHistoricalPredictionScopeError",
    "MissingHistoricalPredictionStartObservationError",
    "MissingRealizedObservationSkip",
    "MixedHistoricalPredictionScopeError",
    "NoEligiblePredictionSnapshotsSkip",
    "SkippedPredictionRecord",
    "TargetObservationNotYetAvailableSkip",
    "UnexpectedHistoricalPredictionReturnCardinalityError",
    "build_historical_prediction_dataset",
]
