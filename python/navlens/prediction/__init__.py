"""Provider-neutral point-in-time NAV return prediction capability."""

from .artifact import (
    SingleReturnPredictionArtifact,
    load_single_return_prediction_artifact,
)
from .contracts import SingleReturnPredictionResult
from .csv import predict_next_published_nav_return_from_csv
from .errors import (
    InsufficientVisibleHistoryError,
    InvalidPredictionArtifactError,
    InvalidPredictionConfigurationError,
    InvalidPredictionWindowError,
    MissingRealizedPriceObservationError,
    NoEligibleSnapshotsError,
    PointInTimePredictionError,
    PredictionArtifactError,
    StaleFundUnitPriceHistoryError,
    UnexpectedRealizedReturnCardinalityError,
    UnsupportedPredictionArtifactSourceError,
)
from .freshness import FundUnitPriceFreshnessPolicy
from .live_evaluation import (
    LivePredictionEvaluationResult,
    evaluate_tefas_prediction_artifact,
)
from .live_evaluation_output import (
    format_live_prediction_evaluation,
    serialize_live_prediction_evaluation,
)
from .options import PredictionModelOptions
from .orchestration import predict_next_published_nav_return_from_snapshots
from .serialization import serialize_single_return_prediction
from .tefas import predict_next_published_nav_return_from_tefas_acquisition
from .text_formatting import format_prediction_text

__all__ = [
    "InsufficientVisibleHistoryError",
    "InvalidPredictionArtifactError",
    "InvalidPredictionConfigurationError",
    "InvalidPredictionWindowError",
    "NoEligibleSnapshotsError",
    "MissingRealizedPriceObservationError",
    "PointInTimePredictionError",
    "PredictionArtifactError",
    "FundUnitPriceFreshnessPolicy",
    "PredictionModelOptions",
    "SingleReturnPredictionResult",
    "SingleReturnPredictionArtifact",
    "StaleFundUnitPriceHistoryError",
    "UnexpectedRealizedReturnCardinalityError",
    "UnsupportedPredictionArtifactSourceError",
    "LivePredictionEvaluationResult",
    "evaluate_tefas_prediction_artifact",
    "format_live_prediction_evaluation",
    "format_prediction_text",
    "load_single_return_prediction_artifact",
    "predict_next_published_nav_return_from_csv",
    "predict_next_published_nav_return_from_snapshots",
    "predict_next_published_nav_return_from_tefas_acquisition",
    "serialize_single_return_prediction",
    "serialize_live_prediction_evaluation",
]
