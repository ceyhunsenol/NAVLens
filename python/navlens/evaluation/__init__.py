"""Chronological model evaluation backed by Rust metrics."""

from .comparison import ModelComparisonEntry, ModelComparisonResult, compare_walk_forward
from .contracts import FittedPrediction, WalkForwardEstimator
from .historical_mean import HistoricalMeanBaseline
from .last_return import LastReturnBaseline
from .linear_baseline import LinearBaselineWalkForward
from .records import WalkForwardRecord
from .result import WalkForwardResult
from .walk_forward import run_walk_forward

__all__ = [
    "FittedPrediction",
    "HistoricalMeanBaseline",
    "LastReturnBaseline",
    "LinearBaselineWalkForward",
    "ModelComparisonEntry",
    "ModelComparisonResult",
    "WalkForwardEstimator",
    "WalkForwardRecord",
    "WalkForwardResult",
    "compare_walk_forward",
    "run_walk_forward",
]
