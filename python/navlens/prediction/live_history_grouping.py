"""Artifact loading and automatic grouping for mixed live prediction evaluation artifacts."""

from collections.abc import Iterable
from pathlib import Path

from .artifact import LivePredictionEvaluationArtifact, load_live_prediction_evaluation_artifacts
from .errors import InvalidLivePredictionHistoryComparisonError
from .live_history import LivePredictionHistoryResult, evaluate_live_prediction_history


def load_grouped_live_prediction_histories(
    paths: Iterable[Path | str],
) -> tuple[LivePredictionHistoryResult, ...]:
    """Load daily mixed-model evaluation artifacts and group by model identity."""
    grouped: dict[tuple[str, str, str], list[LivePredictionEvaluationArtifact]] = {}
    found_any_path = False
    for path in paths:
        found_any_path = True
        artifacts = load_live_prediction_evaluation_artifacts(path)
        for artifact in artifacts:
            model = artifact.prediction_artifact.prediction.model
            key = (model.name, model.version, model.feature_set_version)
            grouped.setdefault(key, []).append(artifact)

    if not found_any_path or not grouped:
        raise InvalidLivePredictionHistoryComparisonError("evaluation artifact list is empty")

    return tuple(
        evaluate_live_prediction_history(tuple(artifacts)) for artifacts in grouped.values()
    )
