"""Skip categorization and corruption tests for historical prediction evaluation."""

from datetime import UTC, datetime

import pytest
from navlens import MarketDate, NavlensValidationError
from navlens.prediction.historical import (
    HistoricalPredictionDataset,
    HistoricalPredictionEvaluationScope,
    HistoricalPredictionRequest,
    InsufficientVisiblePredictionHistorySkip,
    MissingRealizedObservationSkip,
    NoEligiblePredictionSnapshotsSkip,
    SkippedPredictionRecord,
    TargetObservationNotYetAvailableSkip,
    evaluate_historical_prediction_dataset,
)
from navlens.prediction.historical.errors import (
    UnknownHistoricalPredictionOutcomeError,
    UnknownHistoricalPredictionSkipReasonError,
)
from tests.historical_prediction_fixtures import (
    make_real_historical_prediction_dataset,
    make_request,
    make_scope,
)


@pytest.fixture
def mock_scope() -> HistoricalPredictionEvaluationScope:
    return make_scope()


@pytest.fixture
def base_request(mock_scope: HistoricalPredictionEvaluationScope) -> HistoricalPredictionRequest:
    return make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
    )


def test_mixed_success_and_skips(
    mock_scope: HistoricalPredictionEvaluationScope, base_request: HistoricalPredictionRequest
) -> None:
    # Use real orchestrator to build a real success record
    success_dataset = make_real_historical_prediction_dataset((base_request,))
    success_record = success_dataset.outcomes[0]

    req_skip1 = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, 0, tzinfo=UTC),
    )
    req_skip2 = make_request(
        prediction_date=MarketDate(2026, 1, 12),
        target_date=MarketDate(2026, 1, 13),
        prediction_timestamp=datetime(2026, 1, 12, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 13, 18, 0, 0, tzinfo=UTC),
    )
    req_skip3 = make_request(
        prediction_date=MarketDate(2026, 1, 13),
        target_date=MarketDate(2026, 1, 14),
        prediction_timestamp=datetime(2026, 1, 13, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 14, 18, 0, 0, tzinfo=UTC),
    )
    req_skip4 = make_request(
        prediction_date=MarketDate(2026, 1, 14),
        target_date=MarketDate(2026, 1, 15),
        prediction_timestamp=datetime(2026, 1, 14, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 15, 18, 0, 0, tzinfo=UTC),
    )

    skip1 = SkippedPredictionRecord(
        request=req_skip1,
        reason=NoEligiblePredictionSnapshotsSkip(),
    )
    skip2 = SkippedPredictionRecord(
        request=req_skip2,
        reason=InsufficientVisiblePredictionHistorySkip(),
    )
    skip3 = SkippedPredictionRecord(
        request=req_skip3,
        reason=TargetObservationNotYetAvailableSkip(),
    )
    skip4 = SkippedPredictionRecord(
        request=req_skip4,
        reason=MissingRealizedObservationSkip(),
    )

    dataset = HistoricalPredictionDataset(
        scope=mock_scope, outcomes=(success_record, skip1, skip2, skip3, skip4)
    )

    result = evaluate_historical_prediction_dataset(dataset)
    assert result.total_period_count == 5
    assert result.evaluated_period_count == 1
    assert result.skipped_period_count == 4
    assert result.no_eligible_snapshots_count == 1
    assert result.insufficient_history_count == 1
    assert result.target_not_yet_available_count == 1
    assert result.missing_target_observation_count == 1


def test_corrupted_outcome_fails_fast(
    mock_scope: HistoricalPredictionEvaluationScope, base_request: HistoricalPredictionRequest
) -> None:
    skip = SkippedPredictionRecord(
        request=base_request,
        reason=NoEligiblePredictionSnapshotsSkip(),
    )
    dataset = HistoricalPredictionDataset(scope=mock_scope, outcomes=(skip,))

    # Bypass invariant check using object.__setattr__ to inject bad outcome list
    class BadOutcome:
        pass

    object.__setattr__(dataset, "outcomes", (BadOutcome(),))

    with pytest.raises(UnknownHistoricalPredictionOutcomeError):
        evaluate_historical_prediction_dataset(dataset)


def test_corrupted_skip_fails_fast(
    mock_scope: HistoricalPredictionEvaluationScope, base_request: HistoricalPredictionRequest
) -> None:
    skip = SkippedPredictionRecord(
        request=base_request,
        reason=NoEligiblePredictionSnapshotsSkip(),
    )

    class BadReason:
        pass

    # Inject bad skip reason using object.__setattr__
    object.__setattr__(skip, "reason", BadReason())

    dataset = HistoricalPredictionDataset(scope=mock_scope, outcomes=(skip,))

    with pytest.raises(UnknownHistoricalPredictionSkipReasonError):
        evaluate_historical_prediction_dataset(dataset)


def test_rust_chronology_ownership(
    mock_scope: HistoricalPredictionEvaluationScope,
) -> None:
    # Build two real records via orchestrator that are chronologically ordered
    req_early = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
    )
    req_late = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, 0, tzinfo=UTC),
    )

    dataset_builder = make_real_historical_prediction_dataset((req_early, req_late))
    rec_early = dataset_builder.outcomes[0]
    rec_late = dataset_builder.outcomes[1]

    # Normally HistoricalPredictionDataset constructor would enforce chronology of outcomes.
    # We bypass the constructor invariant using object.__setattr__ to inject corrupted order.
    # The late record comes before the early record.
    dataset = HistoricalPredictionDataset(scope=mock_scope, outcomes=tuple())
    object.__setattr__(dataset, "outcomes", (rec_late, rec_early))

    # Should raise native NavlensValidationError because observations are out of order.
    # Match the specific native chronology message.
    with pytest.raises(NavlensValidationError, match="chronological"):
        evaluate_historical_prediction_dataset(dataset)
