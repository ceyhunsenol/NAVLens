"""Deterministic reports for one live prediction evaluation."""

import json

from .artifact_schemas import LIVE_PREDICTION_EVALUATION_SCHEMA_VERSION
from .live_evaluation import LivePredictionEvaluationResult

SCHEMA_VERSION = LIVE_PREDICTION_EVALUATION_SCHEMA_VERSION


def format_live_prediction_evaluation(result: LivePredictionEvaluationResult) -> str:
    """Format predicted-versus-realized values and native one-sample metrics."""
    interval = result.metrics.interval
    lines = [
        "=== NAVLens Live Prediction Evaluation ===",
        f"Fund ID: {result.artifact.fund_id}",
        f"Prediction Date: {result.artifact.prediction_date}",
        f"Target Date: {result.artifact.target_date}",
        f"Evaluated At: {result.evaluated_at.isoformat()}",
        f"Predicted Return (Decimal): {result.artifact.prediction.expected_return:.10f}",
        f"Realized Return (Decimal): {result.realized_return.return_decimal:.10f}",
        f"Absolute Error (Decimal): {result.metrics.mean_absolute_error:.10f}",
        f"Signed Error (Decimal): {result.metrics.mean_error:.10f}",
        f"Direction Correct: {result.metrics.direction_accuracy == 1.0}",
        f"Interval Covered: {interval is not None and interval.coverage == 1.0}",
        f"Source Artifact: {result.source_artifact_path}",
        f"Source Cache Hit: {result.source_from_cache}",
    ]
    return "\n".join(lines)


def serialize_live_prediction_evaluation(result: LivePredictionEvaluationResult) -> bytes:
    """Serialize a live evaluation through a deterministic versioned JSON schema."""
    interval = result.metrics.interval
    payload = {
        "absolute_error_decimal": result.metrics.mean_absolute_error,
        "confidence_level": result.artifact.prediction.confidence_level,
        "direction_correct": result.metrics.direction_accuracy == 1.0,
        "evaluated_at": result.evaluated_at.isoformat(),
        "fund_id": result.artifact.fund_id,
        "feature_schema_version": result.artifact.prediction.model.feature_set_version,
        "interval_covered": interval is not None and interval.coverage == 1.0,
        "last_observation_date": str(result.artifact.last_observation_date),
        "model_name": result.artifact.prediction.model.name,
        "model_version": result.artifact.prediction.model.version,
        "prediction_date": str(result.artifact.prediction_date),
        "prediction_timestamp": result.artifact.prediction_timestamp.isoformat(),
        "predicted_return_decimal": result.artifact.prediction.expected_return,
        "prediction_interval_lower_decimal": result.artifact.prediction.lower_bound,
        "prediction_interval_upper_decimal": result.artifact.prediction.upper_bound,
        "realized_return_decimal": result.realized_return.return_decimal,
        "schema_version": SCHEMA_VERSION,
        "signed_error_decimal": result.metrics.mean_error,
        "source_artifact_path": str(result.source_artifact_path),
        "source_cache_hit": result.source_from_cache,
        "source_id": result.artifact.source_id,
        "target_date": str(result.artifact.target_date),
    }
    return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")
