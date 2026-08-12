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
