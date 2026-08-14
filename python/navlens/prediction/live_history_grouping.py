"""Artifact loading and automatic grouping for mixed live prediction evaluation artifacts."""

from collections.abc import Iterable
from pathlib import Path

from ._model_identity import ModelIdentity, model_identity
from .artifact import LivePredictionEvaluationArtifact, load_live_prediction_evaluation_artifacts
from .errors import InvalidLivePredictionHistoryComparisonError
from .live_history import LivePredictionHistoryResult, evaluate_live_prediction_history


def load_grouped_live_prediction_histories(
    paths: Iterable[Path | str],
) -> tuple[LivePredictionHistoryResult, ...]:
    """Load daily mixed-model evaluation artifacts and group by model identity."""
    artifacts = _load_evaluation_artifacts_single_pass(paths)
    grouped_models = _group_artifacts_by_model(artifacts)
    return tuple(
        evaluate_live_prediction_history(tuple(group)) for group in grouped_models.values()
    )


def _model_identity(artifact: LivePredictionEvaluationArtifact) -> ModelIdentity:
    return model_identity(artifact.prediction_artifact.prediction.model)


def _scope_identity(artifact: LivePredictionEvaluationArtifact) -> tuple[str, str]:
    prediction = artifact.prediction_artifact
    return (prediction.fund_id, prediction.source_id)


def _load_evaluation_artifacts_single_pass(
    paths: Iterable[Path | str],
) -> tuple[LivePredictionEvaluationArtifact, ...]:
    artifacts: list[LivePredictionEvaluationArtifact] = []
    found_any_path = False
    for path in paths:
        found_any_path = True
        artifacts.extend(load_live_prediction_evaluation_artifacts(path))
    if not found_any_path or not artifacts:
        raise InvalidLivePredictionHistoryComparisonError("evaluation artifact list is empty")
    return tuple(artifacts)


def _group_artifacts_by_model(
    artifacts: Iterable[LivePredictionEvaluationArtifact],
) -> dict[tuple[str, str, str], list[LivePredictionEvaluationArtifact]]:
    grouped: dict[tuple[str, str, str], list[LivePredictionEvaluationArtifact]] = {}
    for artifact in artifacts:
        grouped.setdefault(_model_identity(artifact), []).append(artifact)
    return grouped


def _group_artifacts_by_scope(
    artifacts: Iterable[LivePredictionEvaluationArtifact],
) -> dict[tuple[str, str], list[LivePredictionEvaluationArtifact]]:
    grouped: dict[tuple[str, str], list[LivePredictionEvaluationArtifact]] = {}
    for artifact in artifacts:
        grouped.setdefault(_scope_identity(artifact), []).append(artifact)
    return grouped
