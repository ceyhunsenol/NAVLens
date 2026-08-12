"""Loading and validation for versioned single-prediction JSON artifacts."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from navlens import (
    MarketDate,
    ModelDescriptor,
    ReturnPrediction,
    create_return_prediction,
)
from navlens._timestamps import validate_utc_timestamp

from .artifact_batch_payload import require_batch_successes
from .artifact_schemas import (
    LIVE_PREDICTION_EVALUATION_SCHEMA_VERSION,
    SINGLE_RETURN_PREDICTION_SCHEMA_VERSION,
    TEFAS_PREDICTION_EVALUATION_BATCH_SCHEMA_VERSION,
)
from .errors import InvalidPredictionArtifactError

_REQUIRED_KEYS = {
    "confidence_level",
    "expected_return_decimal",
    "feature_schema_version",
    "fund_id",
    "last_observation_date",
    "model_name",
    "model_version",
    "prediction_date",
    "prediction_interval_lower_decimal",
    "prediction_interval_upper_decimal",
    "prediction_timestamp",
    "schema_version",
    "source_id",
    "target_date",
}
_REQUIRED_EVALUATION_KEYS = (_REQUIRED_KEYS - {"expected_return_decimal"}) | {
    "evaluated_at",
    "predicted_return_decimal",
    "realized_return_decimal",
}


@dataclass(frozen=True, slots=True)
class SingleReturnPredictionArtifact:
    """Validated subset required to evaluate one stored prediction."""

    fund_id: str
    source_id: str
    prediction_date: MarketDate
    target_date: MarketDate
    last_observation_date: MarketDate
    prediction_timestamp: datetime
    prediction: ReturnPrediction


@dataclass(frozen=True, slots=True)
class LivePredictionEvaluationArtifact:
    """Validated prediction and realized return loaded from one evaluation artifact."""

    prediction_artifact: SingleReturnPredictionArtifact
    realized_return_decimal: float
    evaluated_at: datetime


def load_single_return_prediction_artifact(
    path: str | Path,
) -> SingleReturnPredictionArtifact:
    """Load a v1 JSON artifact and rebuild its native prediction types."""
    return build_single_return_prediction_artifact(read_prediction_artifact_payload(Path(path)))


def load_live_prediction_evaluation_artifact(
    path: str | Path,
) -> LivePredictionEvaluationArtifact:
    """Load a live-evaluation JSON artifact for aggregate native evaluation."""
    return _build_live_prediction_evaluation_artifact(read_prediction_artifact_payload(Path(path)))


def load_live_prediction_evaluation_artifacts(
    path: str | Path,
) -> tuple[LivePredictionEvaluationArtifact, ...]:
    """Load one evaluation artifact or all successes from one batch artifact."""
    payload = read_prediction_artifact_payload(Path(path))
    if payload.get("schema_version") == LIVE_PREDICTION_EVALUATION_SCHEMA_VERSION:
        return (_build_live_prediction_evaluation_artifact(payload),)
    if payload.get("schema_version") != TEFAS_PREDICTION_EVALUATION_BATCH_SCHEMA_VERSION:
        raise InvalidPredictionArtifactError(
            f"unsupported evaluation artifact schema: {payload.get('schema_version')!r}"
        )
    successes = require_batch_successes(
        payload,
        expected_schema=TEFAS_PREDICTION_EVALUATION_BATCH_SCHEMA_VERSION,
        artifact_kind="evaluation",
    )
    if not successes:
        raise InvalidPredictionArtifactError(
            "evaluation batch must contain at least one successful evaluation"
        )
    return tuple(_build_live_prediction_evaluation_artifact(item) for item in successes)


def _build_live_prediction_evaluation_artifact(
    payload: dict[str, Any],
) -> LivePredictionEvaluationArtifact:
    missing = sorted(_REQUIRED_EVALUATION_KEYS - payload.keys())
    if missing:
        raise InvalidPredictionArtifactError(
            f"evaluation artifact is missing required fields: {', '.join(missing)}"
        )
    if payload["schema_version"] != LIVE_PREDICTION_EVALUATION_SCHEMA_VERSION:
        raise InvalidPredictionArtifactError(
            f"unsupported evaluation artifact schema: {payload['schema_version']!r}"
        )
    prediction_payload = dict(payload)
    prediction_payload["expected_return_decimal"] = payload["predicted_return_decimal"]
    prediction_payload["schema_version"] = SINGLE_RETURN_PREDICTION_SCHEMA_VERSION
    try:
        return LivePredictionEvaluationArtifact(
            build_single_return_prediction_artifact(prediction_payload),
            _number(payload, "realized_return_decimal"),
            _timestamp(payload, "evaluated_at"),
        )
    except InvalidPredictionArtifactError:
        raise
    except (TypeError, ValueError) as error:
        raise InvalidPredictionArtifactError(
            "evaluation artifact contains invalid native prediction values"
        ) from error


def build_single_return_prediction_artifact(
    payload: dict[str, Any],
) -> SingleReturnPredictionArtifact:
    """Validate one payload and rebuild its native prediction types."""
    missing = sorted(_REQUIRED_KEYS - payload.keys())
    if missing:
        raise InvalidPredictionArtifactError(
            f"prediction artifact is missing required fields: {', '.join(missing)}"
        )
    if payload["schema_version"] != SINGLE_RETURN_PREDICTION_SCHEMA_VERSION:
        raise InvalidPredictionArtifactError(
            f"unsupported prediction artifact schema: {payload['schema_version']!r}"
        )
    try:
        artifact = _build_native_artifact(payload)
        _validate_date_order(artifact)
        return artifact
    except InvalidPredictionArtifactError:
        raise
    except (TypeError, ValueError) as error:
        raise InvalidPredictionArtifactError(
            "prediction artifact contains invalid native prediction values"
        ) from error


def _build_native_artifact(payload: dict[str, Any]) -> SingleReturnPredictionArtifact:
    prediction = create_return_prediction(
        _number(payload, "expected_return_decimal"),
        _number(payload, "prediction_interval_lower_decimal"),
        _number(payload, "prediction_interval_upper_decimal"),
        _number(payload, "confidence_level"),
        ModelDescriptor(
            _text(payload, "model_name"),
            _text(payload, "model_version"),
            _text(payload, "feature_schema_version"),
        ),
    )
    return SingleReturnPredictionArtifact(
        _text(payload, "fund_id"),
        _text(payload, "source_id"),
        _market_date(payload, "prediction_date"),
        _market_date(payload, "target_date"),
        _market_date(payload, "last_observation_date"),
        _timestamp(payload, "prediction_timestamp"),
        prediction,
    )


def read_prediction_artifact_payload(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes(), object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise InvalidPredictionArtifactError(f"invalid prediction artifact JSON: {path}") from error
    if not isinstance(value, dict):
        raise InvalidPredictionArtifactError("prediction artifact root must be a JSON object")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise InvalidPredictionArtifactError(f"duplicate prediction artifact field: {key}")
        value[key] = item
    return value


def _text(payload: dict[str, Any], field: str) -> str:
    value = payload[field]
    if not isinstance(value, str) or not value.strip():
        raise InvalidPredictionArtifactError(f"{field} must be a non-empty string")
    return value


def _number(payload: dict[str, Any], field: str) -> float:
    value = payload[field]
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise InvalidPredictionArtifactError(f"{field} must be a number")
    return float(value)


def _market_date(payload: dict[str, Any], field: str) -> MarketDate:
    try:
        value = datetime.strptime(_text(payload, field), "%Y-%m-%d").date()
        return MarketDate(value.year, value.month, value.day)
    except ValueError as error:
        raise InvalidPredictionArtifactError(f"{field} must use YYYY-MM-DD format") from error


def _timestamp(payload: dict[str, Any], field: str) -> datetime:
    try:
        value = datetime.fromisoformat(_text(payload, field))
        validate_utc_timestamp(value, field, InvalidPredictionArtifactError)
        return value
    except ValueError as error:
        raise InvalidPredictionArtifactError(
            f"{field} must be an ISO-8601 UTC timestamp"
        ) from error


def _validate_date_order(artifact: SingleReturnPredictionArtifact) -> None:
    if artifact.last_observation_date > artifact.prediction_date:
        raise InvalidPredictionArtifactError(
            "last_observation_date cannot be after prediction_date"
        )
    if artifact.target_date <= artifact.prediction_date:
        raise InvalidPredictionArtifactError("target_date must be after prediction_date")
