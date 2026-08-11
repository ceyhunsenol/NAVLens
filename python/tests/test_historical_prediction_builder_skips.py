"""Tests for historical prediction dataset builder skip classification and cutoff behavior."""

from datetime import UTC, date, datetime

from navlens import MarketDate
from navlens.prediction.historical import (
    HistoricalPredictionRecord,
    InsufficientVisiblePredictionHistorySkip,
    MissingRealizedObservationSkip,
    NoEligiblePredictionSnapshotsSkip,
    SkippedPredictionRecord,
    TargetObservationNotYetAvailableSkip,
    build_historical_prediction_dataset,
)
from tests.historical_prediction_fixtures import (
    make_request,
    make_scope,
    make_snapshot,
    sample_snapshots,
)


def test_no_eligible_prediction_snapshots_typed_skip() -> None:
    scope = make_scope()
    req = make_request(
        prediction_timestamp=datetime(2025, 1, 1, 18, 0, tzinfo=UTC),
        prediction_date=MarketDate(2025, 1, 1),
        target_date=MarketDate(2025, 1, 2),
        evaluation_timestamp=datetime(2025, 1, 2, 18, 0, tzinfo=UTC),
    )
    snapshots = sample_snapshots(
        base_date=date(2026, 1, 1),
        start_time=datetime(2026, 1, 1, 18, 0, tzinfo=UTC),
        count=10,
    )

    dataset = build_historical_prediction_dataset(scope, [req], snapshots)

    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, SkippedPredictionRecord)
    assert isinstance(rec.reason, NoEligiblePredictionSnapshotsSkip)


def test_insufficient_visible_history_typed_skip() -> None:
    scope = make_scope(lookback=5)
    snapshots = sample_snapshots(count=3)
    req = make_request(
        prediction_date=MarketDate(2026, 1, 3),
        target_date=MarketDate(2026, 1, 4),
        prediction_timestamp=datetime(2026, 1, 3, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 4, 18, 0, tzinfo=UTC),
    )

    dataset = build_historical_prediction_dataset(scope, [req], snapshots)

    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, SkippedPredictionRecord)
    assert isinstance(rec.reason, InsufficientVisiblePredictionHistorySkip)


def test_missing_realized_observation_typed_skip() -> None:
    scope = make_scope(lookback=5)
    snapshots = sample_snapshots(count=10)
    req = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 20),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 20, 18, 0, tzinfo=UTC),
    )

    dataset = build_historical_prediction_dataset(scope, [req], snapshots)

    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, SkippedPredictionRecord)
    assert isinstance(rec.reason, MissingRealizedObservationSkip)


def test_target_exists_only_after_evaluation_timestamp_typed_skip() -> None:
    scope = make_scope(lookback=5)
    snapshots = sample_snapshots(count=10)

    late_target_snap = make_snapshot(
        fund_id="FUND_A",
        source_id="SOURCE_1",
        market_date=date(2026, 1, 11),
        available_at=datetime(2026, 1, 11, 20, 0, tzinfo=UTC),
    )
    snapshots.append(late_target_snap)

    req = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )

    dataset = build_historical_prediction_dataset(scope, [req], snapshots)

    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, SkippedPredictionRecord)
    assert isinstance(rec.reason, TargetObservationNotYetAvailableSkip)


def test_earlier_eligible_target_plus_later_future_correction_succeeds() -> None:
    scope = make_scope(lookback=5)
    snapshots = sample_snapshots(count=10)

    # Target date 2026-01-11 original published at 12:00 (<= 18:00 cutoff)
    early_target_snap = make_snapshot(
        fund_id="FUND_A",
        source_id="SOURCE_1",
        market_date=date(2026, 1, 11),
        price=103.0,
        available_at=datetime(2026, 1, 11, 12, 0, tzinfo=UTC),
    )
    # Target date 2026-01-11 correction published at 22:00 (after 18:00 evaluation cutoff)
    late_correction_snap = make_snapshot(
        fund_id="FUND_A",
        source_id="SOURCE_1",
        market_date=date(2026, 1, 11),
        price=103.5,
        available_at=datetime(2026, 1, 11, 22, 0, tzinfo=UTC),
    )
    snapshots.extend([early_target_snap, late_correction_snap])

    req = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )

    dataset = build_historical_prediction_dataset(scope, [req], snapshots)

    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, HistoricalPredictionRecord)
    assert rec.realized_end_snapshot.observation.unit_price.value == 103.0


def test_evaluation_visible_start_correction_does_not_alter_prediction_result() -> None:
    scope = make_scope(lookback=5)
    snapshots = sample_snapshots(count=10)

    # Start date 2026-01-10 correction published at 2026-01-11 09:00 UTC
    # Prediction timestamp is 2026-01-10 18:00 UTC (prediction cannot observe this correction)
    # Evaluation timestamp is 2026-01-11 18:00 UTC (evaluation observes this correction)
    corrected_start = make_snapshot(
        fund_id="FUND_A",
        source_id="SOURCE_1",
        market_date=date(2026, 1, 10),
        price=999.0,
        available_at=datetime(2026, 1, 11, 9, 0, tzinfo=UTC),
    )
    snapshots.append(corrected_start)

    target_snap = make_snapshot(
        fund_id="FUND_A",
        source_id="SOURCE_1",
        market_date=date(2026, 1, 11),
        price=105.0,
        available_at=datetime(2026, 1, 11, 12, 0, tzinfo=UTC),
    )
    snapshots.append(target_snap)

    req = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )

    dataset = build_historical_prediction_dataset(scope, [req], snapshots)

    assert len(dataset.outcomes) == 1
    rec = dataset.outcomes[0]
    assert isinstance(rec, HistoricalPredictionRecord)

    # Evaluation-visible start snapshot receives the corrected price (999.0)
    assert rec.realized_start_snapshot.observation.unit_price.value == 999.0
    # Prediction result retains the snapshot state visible at prediction timestamp
    pred_start = rec.prediction_result.selected_snapshots[-1]
    assert pred_start.observation.unit_price.value != 999.0
