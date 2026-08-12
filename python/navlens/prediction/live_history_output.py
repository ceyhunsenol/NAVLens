"""Deterministic reports for aggregate live prediction history."""

import json

from .artifact_schemas import LIVE_PREDICTION_HISTORY_SCHEMA_VERSION
from .live_history import LivePredictionHistoryResult


def format_live_prediction_history(result: LivePredictionHistoryResult) -> str:
    """Format native aggregate metrics for one live prediction history."""
    interval = result.metrics.interval
    interval_coverage = "Unavailable" if interval is None else f"{interval.coverage:.10f}"
    interval_width = "Unavailable" if interval is None else f"{interval.mean_width:.10f}"
    lines = [
        "=== NAVLens Live Prediction History ===",
        f"Fund ID: {result.fund_id}",
        f"Source ID: {result.source_id}",
        f"Sample Count: {result.metrics.sample_count}",
        f"Mean Absolute Error: {result.metrics.mean_absolute_error:.10f}",
        f"Mean Error: {result.metrics.mean_error:.10f}",
        f"Root Mean Squared Error: {result.metrics.root_mean_squared_error:.10f}",
        f"Direction Accuracy: {result.metrics.direction_accuracy:.10f}",
        f"Interval Coverage: {interval_coverage}",
        f"Interval Mean Width: {interval_width}",
        f"First Target Date: {result.artifacts[0].prediction_artifact.target_date}",
        f"Last Target Date: {result.artifacts[-1].prediction_artifact.target_date}",
    ]
    return "\n".join(lines)


def serialize_live_prediction_history(result: LivePredictionHistoryResult) -> bytes:
    """Serialize native history metrics through a deterministic JSON schema."""
    interval = result.metrics.interval
    first = result.artifacts[0].prediction_artifact
    payload = {
        "direction_accuracy": result.metrics.direction_accuracy,
        "feature_schema_version": first.prediction.model.feature_set_version,
        "first_target_date": str(first.target_date),
        "fund_id": result.fund_id,
        "interval_coverage": interval.coverage if interval is not None else None,
        "interval_mean_width": interval.mean_width if interval is not None else None,
        "last_target_date": str(result.artifacts[-1].prediction_artifact.target_date),
        "mean_absolute_error_decimal": result.metrics.mean_absolute_error,
        "mean_error_decimal": result.metrics.mean_error,
        "model_name": first.prediction.model.name,
        "model_version": first.prediction.model.version,
        "root_mean_squared_error_decimal": result.metrics.root_mean_squared_error,
        "sample_count": result.metrics.sample_count,
        "schema_version": LIVE_PREDICTION_HISTORY_SCHEMA_VERSION,
        "source_id": result.source_id,
    }
    return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")
