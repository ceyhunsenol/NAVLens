"""Tests for HistoricalPredictionEvaluation text formatting."""

from datetime import UTC, datetime

import pytest
from navlens import MarketDate
from navlens.prediction.historical import (
    HistoricalPredictionDataset,
    HistoricalPredictionEvaluation,
    NoEligiblePredictionSnapshotsSkip,
    SkippedPredictionRecord,
    evaluate_historical_prediction_dataset,
    format_historical_prediction_evaluation,
)
from tests.historical_prediction_fixtures import (
    make_real_historical_prediction_dataset,
    make_request,
    make_scope,
)


def test_invalid_type_raises_type_error() -> None:
    with pytest.raises(TypeError, match="HistoricalPredictionEvaluation"):
        format_historical_prediction_evaluation("invalid_input")  # type: ignore

    with pytest.raises(TypeError, match="HistoricalPredictionEvaluation"):
        format_historical_prediction_evaluation(123)  # type: ignore


def test_empty_evaluation_formatting() -> None:
    evaluation = HistoricalPredictionEvaluation(
        metrics=None,
        scope=None,
        total_period_count=0,
        evaluated_period_count=0,
        skipped_period_count=0,
        no_eligible_snapshots_count=0,
        insufficient_history_count=0,
        target_not_yet_available_count=0,
        missing_target_observation_count=0,
    )

    formatted = format_historical_prediction_evaluation(evaluation)
    assert "Historical Prediction Evaluation" in formatted
    assert "Scope: None" in formatted
    assert "Total Period Count: 0" in formatted
    assert "Backtest Metrics: Unavailable (0 evaluated periods)" in formatted
    assert "WARNING:" not in formatted


def test_all_skipped_evaluation_formatting() -> None:
    req = make_request()
    dataset = make_real_historical_prediction_dataset((req,), snapshots=[])
    evaluation = evaluate_historical_prediction_dataset(dataset)

    formatted = format_historical_prediction_evaluation(evaluation)
    assert "Fund ID: FUND_A" in formatted
    assert "Source ID: SOURCE_1" in formatted
    assert "Lookback: 5" in formatted
    assert "Confidence Level: 0.95" in formatted
    assert "Model Version: v1.0" in formatted
    assert "Minimum Training Returns: None" in formatted
    assert "Total Period Count: 1" in formatted
    assert "Evaluated Period Count: 0" in formatted
    assert "Skipped Period Count: 1" in formatted
    assert "No Eligible Snapshots Count: 1" in formatted
    assert "Backtest Metrics: Unavailable (0 evaluated periods)" in formatted
    assert "WARNING: Skipped periods exist (1 of 1 periods skipped)." in formatted


def test_successful_evaluation_formatting_with_interval() -> None:
    req = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
    )
    dataset = make_real_historical_prediction_dataset((req,))
    evaluation = evaluate_historical_prediction_dataset(dataset)

    formatted = format_historical_prediction_evaluation(evaluation)
    assert "Scope:" in formatted
    assert "Fund ID: FUND_A" in formatted
    assert "Total Period Count: 1" in formatted
    assert "Evaluated Period Count: 1" in formatted
    assert "Skipped Period Count: 0" in formatted
    assert "Backtest Metrics:" in formatted
    assert "Sample Count: 1" in formatted
    assert "Mean Absolute Error (Decimal):" in formatted
    assert "Mean Error (Decimal):" in formatted
    assert "Root Mean Squared Error (Decimal):" in formatted
    assert "Direction Accuracy (Ratio):" in formatted
    assert "Interval Metrics:" in formatted
    assert "Confidence Level: 0.95" in formatted
    assert "Coverage (Ratio):" in formatted
    assert "Mean Width (Decimal):" in formatted
    assert "WARNING:" not in formatted


def test_mixed_success_and_skipped_warning() -> None:
    req_success = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
    )
    success_ds = make_real_historical_prediction_dataset((req_success,))
    success_record = success_ds.outcomes[0]

    req_skip = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, 0, tzinfo=UTC),
    )
    skip_record = SkippedPredictionRecord(
        request=req_skip, reason=NoEligiblePredictionSnapshotsSkip()
    )

    scope = make_scope()
    dataset = HistoricalPredictionDataset(scope=scope, outcomes=(success_record, skip_record))
    evaluation = evaluate_historical_prediction_dataset(dataset)

    formatted = format_historical_prediction_evaluation(evaluation)
    assert "Total Period Count: 2" in formatted
    assert "Evaluated Period Count: 1" in formatted
    assert "Skipped Period Count: 1" in formatted
    assert "Backtest Metrics:" in formatted
    assert "WARNING: Skipped periods exist (1 of 2 periods skipped)." in formatted


def test_deterministic_repeated_output() -> None:
    req = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
    )
    dataset = make_real_historical_prediction_dataset((req,))
    evaluation = evaluate_historical_prediction_dataset(dataset)

    first_output = format_historical_prediction_evaluation(evaluation)
    second_output = format_historical_prediction_evaluation(evaluation)
    assert first_output == second_output


def test_evaluation_state_unmodified() -> None:
    req = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
    )
    dataset = make_real_historical_prediction_dataset((req,))
    evaluation = evaluate_historical_prediction_dataset(dataset)

    scope_before = evaluation.scope
    metrics_before = evaluation.metrics
    total_before = evaluation.total_period_count

    _ = format_historical_prediction_evaluation(evaluation)

    assert evaluation.scope is scope_before
    assert evaluation.metrics is metrics_before
    assert evaluation.total_period_count == total_before
