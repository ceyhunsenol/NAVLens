"""Deterministic versioned JSON bytes serialization for single return prediction results."""

import json

from .artifact_schemas import SINGLE_RETURN_PREDICTION_SCHEMA_VERSION
from .contracts import SingleReturnPredictionResult

SCHEMA_VERSION = SINGLE_RETURN_PREDICTION_SCHEMA_VERSION


def serialize_single_return_prediction(result: SingleReturnPredictionResult) -> bytes:
    """Serialize a SingleReturnPredictionResult to deterministic versioned JSON bytes."""
    payload = {
        "actual_data_as_of": result.actual_data_as_of.isoformat(),
        "canonical_return_count": result.canonical_return_count,
        "confidence_level": result.confidence_level,
        "expected_return_decimal": result.expected_return_decimal,
        "feature_schema_version": result.feature_schema_version,
        "fund_id": result.fund_id,
        "last_observation_available_at": result.last_observation_available_at.isoformat(),
        "last_observation_date": str(result.last_observation_date),
        "last_observation_ingested_at": result.last_observation_ingested_at.isoformat(),
        "lookback": result.lookback,
        "model_name": result.model_name,
        "model_version": result.model_version,
        "prediction_date": str(result.prediction_date),
        "prediction_interval_lower_decimal": result.prediction_interval_lower_decimal,
        "prediction_interval_upper_decimal": result.prediction_interval_upper_decimal,
        "prediction_timestamp": result.prediction_timestamp.isoformat(),
        "pricing_as_of_date": str(result.pricing_as_of_date),
        "schema_version": SCHEMA_VERSION,
        "selected_snapshot_count": result.selected_snapshot_count,
        "source_id": result.source_id,
        "target_date": str(result.target_date),
        "target_definition": result.target_definition,
        "training_return_count": result.training_return_count,
        "training_target_end_date": str(result.training_target_end_date),
        "training_target_start_date": str(result.training_target_start_date),
    }
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
