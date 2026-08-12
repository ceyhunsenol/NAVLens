"""Loading single predictions from individual or batch artifacts."""

from pathlib import Path

from .artifact import (
    SingleReturnPredictionArtifact,
    build_single_return_prediction_artifact,
    read_prediction_artifact_payload,
)
from .artifact_batch_payload import require_batch_successes
from .artifact_schemas import (
    SINGLE_RETURN_PREDICTION_SCHEMA_VERSION,
    TEFAS_PREDICTION_BATCH_SCHEMA_VERSION,
)
from .errors import InvalidPredictionArtifactError


def load_single_return_prediction_artifacts(
    path: str | Path,
) -> tuple[SingleReturnPredictionArtifact, ...]:
    """Load one prediction or successful predictions from one batch artifact."""
    payload = read_prediction_artifact_payload(Path(path))
    if payload.get("schema_version") == SINGLE_RETURN_PREDICTION_SCHEMA_VERSION:
        return (build_single_return_prediction_artifact(payload),)
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
