"""Tests for HistoricalPredictionSkipReason marker types."""

from dataclasses import FrozenInstanceError

import pytest
from navlens.prediction.historical import (
    HistoricalPredictionSkipReason,
    InsufficientVisiblePredictionHistorySkip,
    MissingRealizedObservationSkip,
    NoEligiblePredictionSnapshotsSkip,
    TargetObservationNotYetAvailableSkip,
)


def test_skip_reason_types_are_distinct() -> None:
    reasons = [
        NoEligiblePredictionSnapshotsSkip(),
        InsufficientVisiblePredictionHistorySkip(),
        TargetObservationNotYetAvailableSkip(),
        MissingRealizedObservationSkip(),
    ]
    types = [type(r) for r in reasons]
    assert len(set(types)) == 4


def test_skip_reason_instances_are_immutable() -> None:
    skip = NoEligiblePredictionSnapshotsSkip()
    with pytest.raises((AttributeError, TypeError, FrozenInstanceError)):
        skip.some_attr = 123  # type: ignore[misc]


def test_skip_reasons_satisfy_union_type() -> None:
    def process_skip(reason: HistoricalPredictionSkipReason) -> str:
        match reason:
            case NoEligiblePredictionSnapshotsSkip():
                return "no_eligible"
            case InsufficientVisiblePredictionHistorySkip():
                return "insufficient_history"
            case TargetObservationNotYetAvailableSkip():
                return "not_yet_available"
            case MissingRealizedObservationSkip():
                return "missing_realized"

    assert process_skip(NoEligiblePredictionSnapshotsSkip()) == "no_eligible"
    assert process_skip(InsufficientVisiblePredictionHistorySkip()) == "insufficient_history"
    assert process_skip(TargetObservationNotYetAvailableSkip()) == "not_yet_available"
    assert process_skip(MissingRealizedObservationSkip()) == "missing_realized"


def test_no_missing_start_skip_exists() -> None:
    import navlens.prediction.historical.skip_reason as skip_module

    assert not hasattr(skip_module, "MissingRealizedStartObservationSkip")
