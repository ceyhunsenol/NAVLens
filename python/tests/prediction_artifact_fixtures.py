import json
from pathlib import Path


def prediction_artifact_payload(**overrides) -> dict[str, object]:
    payload: dict[str, object] = {
        "confidence_level": 0.9,
        "expected_return_decimal": 0.01,
        "feature_schema_version": "returns-v1",
        "fund_id": "AAL",
        "last_observation_date": "2026-07-20",
        "model_name": "ridge-baseline",
        "model_version": "v1",
        "prediction_date": "2026-07-20",
        "prediction_interval_lower_decimal": -0.01,
        "prediction_interval_upper_decimal": 0.03,
        "prediction_timestamp": "2026-07-20T12:00:00+00:00",
        "schema_version": "navlens-single-return-prediction-v1",
        "source_id": "tefas",
        "target_date": "2026-07-21",
    }
    payload.update(overrides)
    return payload


def write_prediction_artifact(path: Path, **overrides) -> Path:
    path.write_text(
        json.dumps(prediction_artifact_payload(**overrides)),
        encoding="utf-8",
    )
    return path


def evaluation_artifact_payload(**overrides) -> dict[str, object]:
    prediction = prediction_artifact_payload()
    payload = {
        "confidence_level": prediction["confidence_level"],
        "evaluated_at": "2026-07-21T12:00:00+00:00",
        "feature_schema_version": prediction["feature_schema_version"],
        "fund_id": prediction["fund_id"],
        "last_observation_date": prediction["last_observation_date"],
        "model_name": prediction["model_name"],
        "model_version": prediction["model_version"],
        "predicted_return_decimal": prediction["expected_return_decimal"],
        "prediction_date": prediction["prediction_date"],
        "prediction_interval_lower_decimal": prediction["prediction_interval_lower_decimal"],
        "prediction_interval_upper_decimal": prediction["prediction_interval_upper_decimal"],
        "prediction_timestamp": prediction["prediction_timestamp"],
        "realized_return_decimal": 0.02,
        "schema_version": "navlens-live-prediction-evaluation-v1",
        "source_id": prediction["source_id"],
        "target_date": prediction["target_date"],
    }
    payload.update(overrides)
    return payload


def write_evaluation_artifact(path: Path, **overrides) -> Path:
    path.write_text(
        json.dumps(evaluation_artifact_payload(**overrides)),
        encoding="utf-8",
    )
    return path


def write_evaluation_batch_artifact(
    path: Path,
    items: list[dict[str, object]],
) -> Path:
    payload = {
        "schema_version": "navlens-tefas-prediction-evaluation-batch-v1",
        "evaluated_at": "2026-07-21T12:00:00+00:00",
        "total_count": len(items),
        "succeeded_count": len(items),
        "failed_count": 0,
        "successes": items,
        "failures": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
