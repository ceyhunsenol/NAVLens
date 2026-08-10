"""Typed skip reasons for point-in-time historical prediction evaluation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NoEligiblePredictionSnapshotsSkip:
    """Indicates no price snapshots were eligible at prediction_timestamp."""


@dataclass(frozen=True, slots=True)
class InsufficientVisiblePredictionHistorySkip:
    """Indicates visible training history at prediction_timestamp was insufficient."""


@dataclass(frozen=True, slots=True)
class TargetObservationNotYetAvailableSkip:
    """Indicates target observation exists in input but available_at > evaluation_timestamp."""


@dataclass(frozen=True, slots=True)
class MissingRealizedObservationSkip:
    """Indicates exact target observation date was entirely absent from input."""


HistoricalPredictionSkipReason = (
    NoEligiblePredictionSnapshotsSkip
    | InsufficientVisiblePredictionHistorySkip
    | TargetObservationNotYetAvailableSkip
    | MissingRealizedObservationSkip
)
