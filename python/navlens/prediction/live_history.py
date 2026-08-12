"""Aggregate native metrics for stored live prediction evaluations."""

from collections.abc import Iterable
from dataclasses import dataclass

from navlens import BacktestMetrics, BacktestObservation, evaluate_backtest

from .artifact import LivePredictionEvaluationArtifact
from .errors import InvalidLivePredictionHistoryError


@dataclass(frozen=True, slots=True)
class LivePredictionHistoryResult:
    """One homogeneous artifact series and its canonical native metrics."""

    artifacts: tuple[LivePredictionEvaluationArtifact, ...]
    metrics: BacktestMetrics

    @property
    def fund_id(self) -> str:
        return self.artifacts[0].prediction_artifact.fund_id

    @property
    def source_id(self) -> str:
        return self.artifacts[0].prediction_artifact.source_id


def evaluate_live_prediction_history(
    artifacts: Iterable[LivePredictionEvaluationArtifact],
) -> LivePredictionHistoryResult:
    """Validate one comparable series and delegate aggregate metrics to Rust."""
    materialized = tuple(artifacts)
    if not materialized:
        raise InvalidLivePredictionHistoryError("prediction evaluation history is empty")
    _validate_scope(materialized)
    observations = [
        BacktestObservation(
            item.prediction_artifact.prediction_date,
            item.prediction_artifact.target_date,
            item.prediction_artifact.prediction,
            item.realized_return_decimal,
        )
        for item in materialized
    ]
    metrics = evaluate_backtest(materialized[0].prediction_artifact.fund_id, observations)
    return LivePredictionHistoryResult(materialized, metrics)


def _validate_scope(artifacts: tuple[LivePredictionEvaluationArtifact, ...]) -> None:
    if not all(isinstance(item, LivePredictionEvaluationArtifact) for item in artifacts):
        raise InvalidLivePredictionHistoryError(
            "history items must be LivePredictionEvaluationArtifact instances"
        )
    expected = _scope_key(artifacts[0])
    for artifact in artifacts:
        if _scope_key(artifact) != expected:
            raise InvalidLivePredictionHistoryError(
                "history artifacts must share fund, source, and model identity"
            )


def _scope_key(artifact: LivePredictionEvaluationArtifact) -> tuple[str, ...]:
    prediction = artifact.prediction_artifact
    model = prediction.prediction.model
    return (
        prediction.fund_id,
        prediction.source_id,
        model.name,
        model.version,
        model.feature_set_version,
    )
