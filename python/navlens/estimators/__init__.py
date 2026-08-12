"""Statistical estimators owned by the Python research layer."""

from .contracts import FittedPrediction, NextReturnEstimator
from .historical_mean import HistoricalMeanBaseline
from .last_return import LastReturnBaseline
from .linear_baseline import (
    LinearBaselineArtifact,
    LinearBaselineConfig,
    fit_linear_baseline,
    predict_next_return,
)

__all__ = [
    "FittedPrediction",
    "HistoricalMeanBaseline",
    "LastReturnBaseline",
    "LinearBaselineArtifact",
    "LinearBaselineConfig",
    "NextReturnEstimator",
    "fit_linear_baseline",
    "predict_next_return",
]
