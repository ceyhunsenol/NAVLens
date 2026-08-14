"""Deterministic reports for fair live prediction history comparisons."""

import json

from ._model_identity import ModelIdentity, model_identity
from .artifact_schemas import LIVE_PREDICTION_HISTORY_COMPARISON_SCHEMA_VERSION
from .live_history import LivePredictionHistoryResult
from .live_history_comparison import LivePredictionHistoryComparisonResult


def format_live_prediction_history_comparison(
    result: LivePredictionHistoryComparisonResult,
) -> str:
    """Format model histories without selecting a subjective winner."""
    lines = [
        "=== NAVLens Live Prediction History Comparison ===",
        f"Fund ID: {result.fund_id}",
        f"Source ID: {result.source_id}",
        f"Compared Models: {len(result.histories)}",
    ]
    for history in result.histories:
        lines.extend(("", *_history_lines(history)))
    return "\n".join(lines)


def serialize_live_prediction_history_comparison(
    result: LivePredictionHistoryComparisonResult,
) -> bytes:
    """Serialize comparable native metrics through a versioned JSON schema."""
    first = result.histories[0]
    payload = {
        "confidence_level": _confidence_level(first),
        "fund_id": result.fund_id,
        "histories": [_history_payload(item) for item in result.histories],
        "period_end_date": str(first.artifacts[-1].prediction_artifact.target_date),
        "period_start_date": str(first.artifacts[0].prediction_artifact.prediction_date),
        "sample_count": first.metrics.sample_count,
        "schema_version": LIVE_PREDICTION_HISTORY_COMPARISON_SCHEMA_VERSION,
        "source_id": result.source_id,
    }
    return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")


def _history_lines(history: LivePredictionHistoryResult) -> tuple[str, ...]:
    identity = _model_identity(history)
    metrics = history.metrics
    return (
        f"Model: {identity[0]}@{identity[1]} ({identity[2]})",
        f"  Mean Absolute Error: {metrics.mean_absolute_error:.10f}",
        f"  Mean Error: {metrics.mean_error:.10f}",
        f"  Root Mean Squared Error: {metrics.root_mean_squared_error:.10f}",
        f"  Direction Accuracy: {metrics.direction_accuracy:.10f}",
        f"  Interval Coverage: {_interval_value(history, 'coverage')}",
        f"  Interval Mean Width: {_interval_value(history, 'mean_width')}",
    )


def _history_payload(history: LivePredictionHistoryResult) -> dict[str, object]:
    identity = _model_identity(history)
    interval = history.metrics.interval
    return {
        "direction_accuracy": history.metrics.direction_accuracy,
        "feature_schema_version": identity[2],
        "interval_coverage": interval.coverage if interval is not None else None,
        "interval_mean_width": interval.mean_width if interval is not None else None,
        "mean_absolute_error_decimal": history.metrics.mean_absolute_error,
        "mean_error_decimal": history.metrics.mean_error,
        "model_name": identity[0],
        "model_version": identity[1],
        "root_mean_squared_error_decimal": history.metrics.root_mean_squared_error,
    }


def _model_identity(history: LivePredictionHistoryResult) -> ModelIdentity:
    model = history.artifacts[0].prediction_artifact.prediction.model
    return model_identity(model)


def _confidence_level(history: LivePredictionHistoryResult) -> float:
    return history.artifacts[0].prediction_artifact.prediction.confidence_level


def _interval_value(history: LivePredictionHistoryResult, field: str) -> str:
    interval = history.metrics.interval
    return "Unavailable" if interval is None else f"{getattr(interval, field):.10f}"
