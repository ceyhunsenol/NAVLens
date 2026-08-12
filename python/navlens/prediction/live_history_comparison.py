"""Fair comparison contracts for evaluated live prediction histories."""

from collections.abc import Iterable
from dataclasses import dataclass

from .errors import InvalidLivePredictionHistoryComparisonError
from .live_history import LivePredictionHistoryResult


@dataclass(frozen=True, slots=True)
class LivePredictionHistoryComparisonResult:
    """Comparable model histories over one identical realized period sequence."""

    histories: tuple[LivePredictionHistoryResult, ...]

    @property
    def fund_id(self) -> str:
        return self.histories[0].fund_id

    @property
    def source_id(self) -> str:
        return self.histories[0].source_id


def compare_live_prediction_histories(
    histories: Iterable[LivePredictionHistoryResult],
) -> LivePredictionHistoryComparisonResult:
    """Validate fair live-model comparison without recomputing native metrics."""
    materialized = tuple(histories)
    if len(materialized) < 2:
        raise InvalidLivePredictionHistoryComparisonError(
            "comparison requires at least two prediction histories"
        )
    if not all(isinstance(item, LivePredictionHistoryResult) for item in materialized):
        raise InvalidLivePredictionHistoryComparisonError(
            "comparison items must be LivePredictionHistoryResult instances"
        )
    _validate_shared_scope(materialized)
    _validate_model_identity(materialized)
    _validate_periods_and_realizations(materialized)
    _validate_confidence_level(materialized)
    return LivePredictionHistoryComparisonResult(materialized)


def _validate_shared_scope(histories: tuple[LivePredictionHistoryResult, ...]) -> None:
    scopes = {(item.fund_id, item.source_id) for item in histories}
    if len(scopes) != 1:
        raise InvalidLivePredictionHistoryComparisonError(
            "compared histories must share fund and source identity"
        )


def _validate_model_identity(histories: tuple[LivePredictionHistoryResult, ...]) -> None:
    identities = tuple(_model_identity(item) for item in histories)
    if len(set(identities)) != len(identities):
        raise InvalidLivePredictionHistoryComparisonError(
            "compared histories must have unique model identities"
        )


def _validate_periods_and_realizations(
    histories: tuple[LivePredictionHistoryResult, ...],
) -> None:
    periods = {_periods(item) for item in histories}
    if len(periods) != 1:
        raise InvalidLivePredictionHistoryComparisonError(
            "compared histories must use identical prediction and target dates"
        )
    realizations = {_realizations(item) for item in histories}
    if len(realizations) != 1:
        raise InvalidLivePredictionHistoryComparisonError(
            "compared histories must use identical realized returns"
        )


def _validate_confidence_level(
    histories: tuple[LivePredictionHistoryResult, ...],
) -> None:
    confidence_levels = {_confidence_level(item) for item in histories}
    if len(confidence_levels) != 1:
        raise InvalidLivePredictionHistoryComparisonError(
            "compared histories must use an identical confidence level"
        )


def _model_identity(history: LivePredictionHistoryResult) -> tuple[str, str, str]:
    model = history.artifacts[0].prediction_artifact.prediction.model
    return model.name, model.version, model.feature_set_version


def _periods(history: LivePredictionHistoryResult) -> tuple[tuple[object, object], ...]:
    return tuple(
        (item.prediction_artifact.prediction_date, item.prediction_artifact.target_date)
        for item in history.artifacts
    )


def _realizations(history: LivePredictionHistoryResult) -> tuple[float, ...]:
    return tuple(item.realized_return_decimal for item in history.artifacts)


def _confidence_level(history: LivePredictionHistoryResult) -> float:
    return history.artifacts[0].prediction_artifact.prediction.confidence_level
