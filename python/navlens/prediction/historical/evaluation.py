"""Evaluation orchestrator for point-in-time historical prediction datasets."""

from collections.abc import Iterable
from dataclasses import dataclass

from navlens import BacktestMetrics, BacktestObservation, evaluate_backtest

from .dataset import HistoricalPredictionDataset
from .errors import (
    InvalidHistoricalPredictionEvaluationError,
    UnknownHistoricalPredictionOutcomeError,
    UnknownHistoricalPredictionSkipReasonError,
    UnsupportedHistoricalPredictionDatasetError,
)
from .outcome import HistoricalPredictionRecord, SkippedPredictionRecord
from .scope import HistoricalPredictionEvaluationScope
from .skip_reason import (
    InsufficientVisiblePredictionHistorySkip,
    MissingRealizedObservationSkip,
    NoEligiblePredictionSnapshotsSkip,
    TargetObservationNotYetAvailableSkip,
)


@dataclass(frozen=True, slots=True)
class _EvaluationCollection:
    observations: tuple[BacktestObservation, ...]
    no_eligible_snapshots_count: int
    insufficient_history_count: int
    target_not_yet_available_count: int
    missing_target_observation_count: int


@dataclass(frozen=True, slots=True)
class HistoricalPredictionEvaluation:
    """Native backtest metrics and provenance for one point-in-time prediction dataset."""

    metrics: BacktestMetrics | None
    scope: HistoricalPredictionEvaluationScope | None
    total_period_count: int
    evaluated_period_count: int
    skipped_period_count: int
    no_eligible_snapshots_count: int
    insufficient_history_count: int
    target_not_yet_available_count: int
    missing_target_observation_count: int

    def __post_init__(self) -> None:
        """Validate evaluation invariants upon construction."""
        for name, value in (
            ("total_period_count", self.total_period_count),
            ("evaluated_period_count", self.evaluated_period_count),
            ("skipped_period_count", self.skipped_period_count),
            ("no_eligible_snapshots_count", self.no_eligible_snapshots_count),
            ("insufficient_history_count", self.insufficient_history_count),
            ("target_not_yet_available_count", self.target_not_yet_available_count),
            ("missing_target_observation_count", self.missing_target_observation_count),
        ):
            _validate_count(name, value)

        _validate_count_relationships(self)
        _validate_scope_relationship(self)
        _validate_metrics_relationship(self)


def _validate_count(name: str, value: object) -> None:
    if type(value) is not int:
        raise InvalidHistoricalPredictionEvaluationError(
            f"{name} must be a non-bool integer, got {type(value).__name__}"
        )
    if value < 0:
        raise InvalidHistoricalPredictionEvaluationError(
            f"{name} must be non-negative, got {value}"
        )


def _validate_count_relationships(result: HistoricalPredictionEvaluation) -> None:
    if result.evaluated_period_count + result.skipped_period_count != result.total_period_count:
        raise InvalidHistoricalPredictionEvaluationError(
            f"evaluated ({result.evaluated_period_count}) + "
            f"skipped ({result.skipped_period_count}) != total ({result.total_period_count})"
        )
    sum_skips = (
        result.no_eligible_snapshots_count
        + result.insufficient_history_count
        + result.target_not_yet_available_count
        + result.missing_target_observation_count
    )
    if sum_skips != result.skipped_period_count:
        raise InvalidHistoricalPredictionEvaluationError(
            f"skip categories sum ({sum_skips}) != "
            f"skipped_period_count ({result.skipped_period_count})"
        )


def _validate_scope_relationship(result: HistoricalPredictionEvaluation) -> None:
    if result.total_period_count == 0:
        if result.scope is not None:
            raise InvalidHistoricalPredictionEvaluationError(
                "scope must be None when total_period_count is 0"
            )
        return
    if result.scope is None:
        raise InvalidHistoricalPredictionEvaluationError(
            "scope must be non-None when total_period_count > 0"
        )
    if not isinstance(result.scope, HistoricalPredictionEvaluationScope):
        raise InvalidHistoricalPredictionEvaluationError(
            f"scope must be HistoricalPredictionEvaluationScope, got {type(result.scope).__name__}"
        )


def _validate_metrics_relationship(result: HistoricalPredictionEvaluation) -> None:
    if result.evaluated_period_count == 0:
        if result.metrics is not None:
            raise InvalidHistoricalPredictionEvaluationError(
                "metrics must be None when evaluated_period_count is 0"
            )
        return
    if result.metrics is None:
        raise InvalidHistoricalPredictionEvaluationError(
            "metrics must be non-None when evaluated_period_count > 0"
        )
    if not isinstance(result.metrics, BacktestMetrics):
        raise InvalidHistoricalPredictionEvaluationError(
            f"metrics must be BacktestMetrics, got {type(result.metrics).__name__}"
        )
    if result.metrics.sample_count != result.evaluated_period_count:
        raise InvalidHistoricalPredictionEvaluationError(
            f"metrics.sample_count ({result.metrics.sample_count}) != "
            f"evaluated_period_count ({result.evaluated_period_count})"
        )


def _map_record_to_observation(outcome: HistoricalPredictionRecord) -> BacktestObservation:
    return BacktestObservation(
        prediction_date=outcome.request.prediction_date,
        target_date=outcome.request.target_date,
        prediction=outcome.prediction_result.prediction,
        actual_return=outcome.realized_period_return.return_decimal,
    )


def _classify_skip_reason(reason: object) -> type:
    t = type(reason)
    if t in (
        NoEligiblePredictionSnapshotsSkip,
        InsufficientVisiblePredictionHistorySkip,
        TargetObservationNotYetAvailableSkip,
        MissingRealizedObservationSkip,
    ):
        return t
    raise UnknownHistoricalPredictionSkipReasonError(f"Unknown skip reason: {t.__name__}")


def _collect_evaluation_inputs(
    outcomes: Iterable[object],
) -> _EvaluationCollection:
    observations: list[BacktestObservation] = []
    no_eligible_snapshots_count = 0
    insufficient_history_count = 0
    target_not_yet_available_count = 0
    missing_target_observation_count = 0
    for outcome in outcomes:
        if isinstance(outcome, HistoricalPredictionRecord):
            observations.append(_map_record_to_observation(outcome))
        elif isinstance(outcome, SkippedPredictionRecord):
            t = _classify_skip_reason(outcome.reason)
            if t is NoEligiblePredictionSnapshotsSkip:
                no_eligible_snapshots_count += 1
            elif t is InsufficientVisiblePredictionHistorySkip:
                insufficient_history_count += 1
            elif t is TargetObservationNotYetAvailableSkip:
                target_not_yet_available_count += 1
            elif t is MissingRealizedObservationSkip:
                missing_target_observation_count += 1
        else:
            raise UnknownHistoricalPredictionOutcomeError(
                f"Unknown outcome type: {type(outcome).__name__}"
            )
    return _EvaluationCollection(
        observations=tuple(observations),
        no_eligible_snapshots_count=no_eligible_snapshots_count,
        insufficient_history_count=insufficient_history_count,
        target_not_yet_available_count=target_not_yet_available_count,
        missing_target_observation_count=missing_target_observation_count,
    )


def evaluate_historical_prediction_dataset(
    dataset: HistoricalPredictionDataset,
) -> HistoricalPredictionEvaluation:
    """Evaluate one point-in-time prediction dataset using canonical Rust metrics."""
    if not isinstance(dataset, HistoricalPredictionDataset):
        raise UnsupportedHistoricalPredictionDatasetError(
            f"Unsupported dataset type: {type(dataset).__name__}"
        )

    collection = _collect_evaluation_inputs(dataset.outcomes)
    evaluated = len(collection.observations)
    skipped = (
        collection.no_eligible_snapshots_count
        + collection.insufficient_history_count
        + collection.target_not_yet_available_count
        + collection.missing_target_observation_count
    )

    metrics = None
    if evaluated > 0:
        metrics = evaluate_backtest(dataset.scope.fund_id, collection.observations)

    scope = dataset.scope if evaluated + skipped > 0 else None
    return HistoricalPredictionEvaluation(
        metrics=metrics,
        scope=scope,
        total_period_count=evaluated + skipped,
        evaluated_period_count=evaluated,
        skipped_period_count=skipped,
        no_eligible_snapshots_count=collection.no_eligible_snapshots_count,
        insufficient_history_count=collection.insufficient_history_count,
        target_not_yet_available_count=collection.target_not_yet_available_count,
        missing_target_observation_count=collection.missing_target_observation_count,
    )
