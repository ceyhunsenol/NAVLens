"""Explicit JSON serialization for backtest run manifests."""

import json
from typing import Any

from .records import (
    BacktestRunManifest,
    MetricsManifest,
    ModelRunManifest,
    PredictionManifest,
)


def serialize_run_manifest(manifest: BacktestRunManifest) -> bytes:
    """Serialize the versioned contract as deterministic UTF-8 JSON."""
    payload = {
        "schema_version": manifest.schema_version,
        "run_id": manifest.run_id,
        "generated_at": manifest.generated_at.isoformat(),
        "fund_id": manifest.fund_id,
        "target_definition": manifest.target_definition,
        "configuration": {
            "initial_training_returns": manifest.configuration.initial_training_returns,
            "confidence_level": manifest.configuration.confidence_level,
            "linear_lookback": manifest.configuration.linear_lookback,
        },
        "source": {
            "provider": manifest.source.provider,
            "path": manifest.source.path,
            "sha256": manifest.source.sha256,
            "from_cache": manifest.source.from_cache,
            "acquisition_as_of": manifest.source.acquisition_as_of.isoformat(),
            "requested_start_date": manifest.source.requested_start_date.isoformat(),
            "requested_end_date": manifest.source.requested_end_date.isoformat(),
            "source_record_count": manifest.source.source_record_count,
        },
        "models": [_model_payload(model) for model in manifest.models],
    }
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()


def _model_payload(model: ModelRunManifest) -> dict[str, Any]:
    return {
        "model_name": model.model_name,
        "model_version": model.model_version,
        "feature_schema_version": model.feature_schema_version,
        "metrics": _metrics_payload(model.metrics),
        "predictions": [_prediction_payload(value) for value in model.predictions],
    }


def _metrics_payload(metrics: MetricsManifest) -> dict[str, int | float | None]:
    return {
        "sample_count": metrics.sample_count,
        "mean_absolute_error_decimal": metrics.mean_absolute_error_decimal,
        "mean_error_decimal": metrics.mean_error_decimal,
        "root_mean_squared_error_decimal": metrics.root_mean_squared_error_decimal,
        "direction_accuracy": metrics.direction_accuracy,
        "interval_coverage": metrics.interval_coverage,
        "interval_mean_width_decimal": metrics.interval_mean_width_decimal,
    }


def _prediction_payload(prediction: PredictionManifest) -> dict[str, str | float]:
    return {
        "prediction_date": prediction.prediction_date.isoformat(),
        "target_date": prediction.target_date.isoformat(),
        "predicted_return_decimal": prediction.predicted_return_decimal,
        "actual_return_decimal": prediction.actual_return_decimal,
        "lower_bound_decimal": prediction.lower_bound_decimal,
        "upper_bound_decimal": prediction.upper_bound_decimal,
        "training_start": prediction.training_start.isoformat(),
        "training_end": prediction.training_end.isoformat(),
    }
