"""Provider-neutral point-in-time NAV return prediction capability."""

from .contracts import SingleReturnPredictionResult
from .csv import predict_next_published_nav_return_from_csv
from .errors import (
    InsufficientVisibleHistoryError,
    InvalidPredictionConfigurationError,
    InvalidPredictionWindowError,
    NoEligibleSnapshotsError,
    PointInTimePredictionError,
)
from .orchestration import predict_next_published_nav_return_from_snapshots
from .serialization import serialize_single_return_prediction
from .text_formatting import format_prediction_text

__all__ = [
    "InsufficientVisibleHistoryError",
    "InvalidPredictionConfigurationError",
    "InvalidPredictionWindowError",
    "NoEligibleSnapshotsError",
    "PointInTimePredictionError",
    "SingleReturnPredictionResult",
    "format_prediction_text",
    "predict_next_published_nav_return_from_csv",
    "predict_next_published_nav_return_from_snapshots",
    "serialize_single_return_prediction",
]
