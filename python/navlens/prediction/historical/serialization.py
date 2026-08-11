"""Explicit JSON serialization for historical prediction evaluation summaries."""

import json
from typing import Any

from navlens import BacktestMetrics, IntervalMetrics

from .evaluation import HistoricalPredictionEvaluation
from .scope import HistoricalPredictionEvaluationScope

_SCHEMA_VERSION = 1


def serialize_historical_prediction_evaluation(
    evaluation: HistoricalPredictionEvaluation,
) -> bytes:
    """Serialize a HistoricalPredictionEvaluation as deterministic UTF-8 JSON bytes."""
    if not isinstance(evaluation, HistoricalPredictionEvaluation):
        target_type = type(evaluation).__name__
        raise TypeError(
            f"evaluation must be a HistoricalPredictionEvaluation instance, got {target_type}"
        )

    return _encode_json(_evaluation_payload(evaluation))


def _evaluation_payload(evaluation: HistoricalPredictionEvaluation) -> dict[str, Any]:
    return {
        "counts": _counts_payload(evaluation),
        "metrics": _metrics_payload(evaluation.metrics),
        "schema_version": _SCHEMA_VERSION,
        "scope": _scope_payload(evaluation.scope),
    }


def _encode_json(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _scope_payload(
    scope: HistoricalPredictionEvaluationScope | None,
) -> dict[str, Any] | None:
    if scope is None:
        return None

    return {
        "confidence_level": scope.confidence_level,
        "fund_id": scope.fund_id,
        "lookback": scope.lookback,
        "minimum_training_returns": scope.minimum_training_returns,
        "model_version": scope.model_version,
        "source_id": scope.source_id,
    }


def _counts_payload(evaluation: HistoricalPredictionEvaluation) -> dict[str, int]:
    return {
        "evaluated_period_count": evaluation.evaluated_period_count,
        "insufficient_history_count": evaluation.insufficient_history_count,
        "missing_target_observation_count": evaluation.missing_target_observation_count,
        "no_eligible_snapshots_count": evaluation.no_eligible_snapshots_count,
        "skipped_period_count": evaluation.skipped_period_count,
        "target_not_yet_available_count": evaluation.target_not_yet_available_count,
        "total_period_count": evaluation.total_period_count,
    }


def _metrics_payload(metrics: BacktestMetrics | None) -> dict[str, Any] | None:
    if metrics is None:
        return None

    return {
        "direction_accuracy_ratio": metrics.direction_accuracy,
        "interval": _interval_payload(metrics.interval),
        "mean_absolute_error_decimal": metrics.mean_absolute_error,
        "mean_error_decimal": metrics.mean_error,
        "root_mean_squared_error_decimal": metrics.root_mean_squared_error,
        "sample_count": metrics.sample_count,
    }


def _interval_payload(interval: IntervalMetrics | None) -> dict[str, Any] | None:
    if interval is None:
        return None

    return {
        "confidence_level": interval.confidence_level,
        "coverage_ratio": interval.coverage,
        "mean_width_decimal": interval.mean_width,
        "sample_count": interval.sample_count,
    }
