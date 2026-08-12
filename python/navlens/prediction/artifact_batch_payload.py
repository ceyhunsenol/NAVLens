"""Shared validation for versioned batch artifact envelopes."""

from typing import Any

from .errors import InvalidPredictionArtifactError

_REQUIRED_KEYS = {
    "failed_count",
    "failures",
    "schema_version",
    "succeeded_count",
    "successes",
    "total_count",
}


def require_batch_successes(
    payload: dict[str, Any],
    *,
    expected_schema: str,
    artifact_kind: str,
) -> list[dict[str, Any]]:
    """Return validated success objects from a deterministic batch envelope."""
    missing = sorted(_REQUIRED_KEYS - payload.keys())
    if missing:
        raise InvalidPredictionArtifactError(
            f"{artifact_kind} batch is missing required fields: {', '.join(missing)}"
        )
    if payload["schema_version"] != expected_schema:
        raise InvalidPredictionArtifactError(
            f"unsupported {artifact_kind} artifact schema: {payload['schema_version']!r}"
        )
    successes = payload["successes"]
    failures = payload["failures"]
    if not isinstance(successes, list) or not all(isinstance(item, dict) for item in successes):
        raise InvalidPredictionArtifactError(f"{artifact_kind} batch successes must be objects")
    if not isinstance(failures, list):
        raise InvalidPredictionArtifactError(f"{artifact_kind} batch failures must be a list")
    _validate_counts(payload, len(successes), len(failures), artifact_kind)
    return successes


def _validate_counts(
    payload: dict[str, Any], succeeded: int, failed: int, artifact_kind: str
) -> None:
    counts = tuple(
        _strict_count(payload, field)
        for field in ("succeeded_count", "failed_count", "total_count")
    )
    if counts != (succeeded, failed, succeeded + failed):
        raise InvalidPredictionArtifactError(
            f"{artifact_kind} batch counts do not match its outcomes"
        )


def _strict_count(payload: dict[str, Any], field: str) -> int:
    value = payload[field]
    if type(value) is not int or value < 0:
        raise InvalidPredictionArtifactError(f"{field} must be a non-negative integer")
    return value
