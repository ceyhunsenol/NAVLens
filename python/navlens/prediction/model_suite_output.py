"""Deterministic text and JSON output for same-snapshot model suites."""

import json

from .artifact_schemas import PREDICTION_MODEL_SUITE_SCHEMA_VERSION
from .model_suite import PredictionModelSuiteResult
from .serialization import serialize_single_return_prediction


def format_prediction_model_suite(result: PredictionModelSuiteResult) -> str:
    """Render one compact row per model without declaring an arbitrary winner."""
    first = result.predictions[0]
    lines = [
        "=== NAVLens Same-Snapshot Prediction Model Suite ===",
        f"Fund ID: {first.fund_id}",
        f"Prediction Timestamp: {first.prediction_timestamp.isoformat()}",
        f"Prediction Date: {first.prediction_date}",
        f"Target Date: {first.target_date}",
        "model,expected_return_decimal,interval_lower_decimal,interval_upper_decimal",
    ]
    lines.extend(
        f"{item.model_name}@{item.model_version},{item.expected_return_decimal},"
        f"{item.prediction_interval_lower_decimal},{item.prediction_interval_upper_decimal}"
        for item in result.predictions
    )
    return "\n".join(lines)


def serialize_prediction_model_suite(result: PredictionModelSuiteResult) -> bytes:
    """Serialize a suite by embedding canonical single-prediction artifacts."""
    payload = {
        "predictions": [
            json.loads(serialize_single_return_prediction(item)) for item in result.predictions
        ],
        "schema_version": PREDICTION_MODEL_SUITE_SCHEMA_VERSION,
    }
    return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")
