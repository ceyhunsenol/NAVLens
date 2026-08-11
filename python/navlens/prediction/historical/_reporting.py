"""Shared audit-report mappings for historical prediction outcomes."""

from .skip_reason import (
    InsufficientVisiblePredictionHistorySkip,
    MissingRealizedObservationSkip,
    NoEligiblePredictionSnapshotsSkip,
    TargetObservationNotYetAvailableSkip,
)


def skip_reason_code(reason: object) -> str:
    """Return the stable external code for a typed historical prediction skip."""
    codes = {
        NoEligiblePredictionSnapshotsSkip: "no_eligible_prediction_snapshots",
        InsufficientVisiblePredictionHistorySkip: "insufficient_visible_prediction_history",
        TargetObservationNotYetAvailableSkip: "target_observation_not_yet_available",
        MissingRealizedObservationSkip: "missing_realized_observation",
    }
    try:
        return codes[type(reason)]
    except KeyError as error:
        name = type(reason).__name__
        raise TypeError(f"unsupported historical prediction skip: {name}") from error
