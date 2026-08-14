"""Loading single predictions from individual or batch artifacts."""

from pathlib import Path

from .artifact import (
    SingleReturnPredictionArtifact,
    build_single_return_prediction_artifact,
    read_prediction_artifact_payload,
)
from .artifact_batch_payload import require_batch_successes
from .artifact_schemas import (
    PREDICTION_MODEL_SUITE_SCHEMA_VERSION,
    SINGLE_RETURN_PREDICTION_SCHEMA_VERSION,
    TEFAS_PREDICTION_BATCH_SCHEMA_VERSION,
    TEFAS_PREDICTION_MODEL_SUITE_BATCH_SCHEMA_VERSION,
)
from .errors import InvalidPredictionArtifactError
from .options import PredictionModelKind


def load_single_return_prediction_artifacts(
    path: str | Path,
) -> tuple[SingleReturnPredictionArtifact, ...]:
    """Load one prediction or successful predictions from one batch artifact."""
    payload = read_prediction_artifact_payload(Path(path))
    schema = payload.get("schema_version")
    if schema == SINGLE_RETURN_PREDICTION_SCHEMA_VERSION:
        return (build_single_return_prediction_artifact(payload),)
    if schema == PREDICTION_MODEL_SUITE_SCHEMA_VERSION:
        return _load_model_suite(payload)
    if schema == TEFAS_PREDICTION_MODEL_SUITE_BATCH_SCHEMA_VERSION:
        return _load_model_suite_batch(payload)
    successes = require_batch_successes(
        payload,
        expected_schema=TEFAS_PREDICTION_BATCH_SCHEMA_VERSION,
        artifact_kind="prediction",
    )
    if not successes:
        raise InvalidPredictionArtifactError(
            "prediction batch must contain at least one successful prediction"
        )
    return tuple(build_single_return_prediction_artifact(item) for item in successes)


def _load_model_suite_batch(
    payload: dict[str, object],
) -> tuple[SingleReturnPredictionArtifact, ...]:
    successes = require_batch_successes(
        payload,
        expected_schema=TEFAS_PREDICTION_MODEL_SUITE_BATCH_SCHEMA_VERSION,
        artifact_kind="prediction model suite",
    )
    if not successes:
        raise InvalidPredictionArtifactError(
            "prediction model suite batch must contain at least one successful suite"
        )
    artifacts: list[SingleReturnPredictionArtifact] = []
    for item in successes:
        artifacts.extend(_load_model_suite(item))
    return tuple(artifacts)


def _load_model_suite(
    payload: dict[str, object],
) -> tuple[SingleReturnPredictionArtifact, ...]:
    predictions = payload.get("predictions")
    if not isinstance(predictions, list) or len(predictions) != len(PredictionModelKind):
        raise InvalidPredictionArtifactError(
            "prediction model suite must contain every implemented model"
        )
    if not all(isinstance(item, dict) for item in predictions):
        raise InvalidPredictionArtifactError("prediction model suite entries must be JSON objects")
    artifacts = tuple(build_single_return_prediction_artifact(item) for item in predictions)
    if len({item.prediction.model.name for item in artifacts}) != len(artifacts):
        raise InvalidPredictionArtifactError(
            "prediction model suite must contain unique model identities"
        )
    expected_scope = _artifact_scope(artifacts[0])
    if not all(_artifact_scope(item) == expected_scope for item in artifacts):
        raise InvalidPredictionArtifactError(
            "prediction model suite entries must share point-in-time scope"
        )
    return artifacts


def _artifact_scope(artifact: SingleReturnPredictionArtifact) -> tuple[object, ...]:
    return (
        artifact.fund_id,
        artifact.source_id,
        artifact.prediction_date,
        artifact.target_date,
        artifact.last_observation_date,
        artifact.prediction_timestamp,
        artifact.prediction.confidence_level,
        artifact.prediction.model.version,
    )
