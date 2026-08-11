"""Provider-neutral point-in-time historical prediction contracts."""

from .builder import build_historical_prediction_dataset
from .dataset import HistoricalPredictionDataset
from .errors import (
    DecreasingHistoricalPredictionScheduleError,
    DuplicateHistoricalPredictionScheduleError,
    HistoricalPredictionDatasetError,
    InvalidHistoricalPredictionDatasetError,
    InvalidHistoricalPredictionEvaluationError,
    InvalidHistoricalPredictionOutcomeError,
    InvalidHistoricalPredictionRequestError,
    InvalidHistoricalPredictionScopeError,
    MissingHistoricalPredictionStartObservationError,
    MixedHistoricalPredictionScopeError,
    UnexpectedHistoricalPredictionReturnCardinalityError,
    UnknownHistoricalPredictionOutcomeError,
    UnknownHistoricalPredictionSkipReasonError,
    UnsupportedHistoricalPredictionDatasetError,
)
from .evaluation import (
    HistoricalPredictionEvaluation,
    evaluate_historical_prediction_dataset,
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
    "HistoricalPredictionEvaluation",
    "HistoricalPredictionEvaluationScope",
    "HistoricalPredictionOutcome",
    "HistoricalPredictionRecord",
    "HistoricalPredictionRequest",
    "HistoricalPredictionSkipReason",
    "InsufficientVisiblePredictionHistorySkip",
    "InvalidHistoricalPredictionDatasetError",
    "InvalidHistoricalPredictionEvaluationError",
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
    "UnknownHistoricalPredictionOutcomeError",
    "UnknownHistoricalPredictionSkipReasonError",
    "UnsupportedHistoricalPredictionDatasetError",
    "build_historical_prediction_dataset",
    "evaluate_historical_prediction_dataset",
]
