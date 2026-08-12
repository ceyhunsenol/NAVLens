"""Artifact loading composition for one evaluated prediction history."""

from collections.abc import Iterable
from pathlib import Path

from .artifact import load_live_prediction_evaluation_artifacts
from .live_history import LivePredictionHistoryResult, evaluate_live_prediction_history


def load_live_prediction_history(paths: Iterable[Path]) -> LivePredictionHistoryResult:
    """Load explicit single or batch artifacts and evaluate one homogeneous history."""
    groups = tuple(load_live_prediction_evaluation_artifacts(path) for path in paths)
    artifacts = tuple(item for group in groups for item in group)
    return evaluate_live_prediction_history(artifacts)
