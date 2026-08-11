"""Contract tests for HistoricalPredictionEvaluation."""

import pytest
from navlens import (
    BacktestMetrics,
    BacktestObservation,
    MarketDate,
    ModelDescriptor,
    create_return_prediction,
    evaluate_backtest,
)
from navlens.prediction.historical import (
    HistoricalPredictionEvaluation,
    HistoricalPredictionEvaluationScope,
    InvalidHistoricalPredictionEvaluationError,
)


@pytest.fixture
def mock_scope() -> HistoricalPredictionEvaluationScope:
    return HistoricalPredictionEvaluationScope(
        fund_id="fund1",
        source_id="src1",
        lookback=30,
        confidence_level=0.95,
        model_version="1.0",
        minimum_training_returns=None,
    )


@pytest.fixture
def native_metrics() -> BacktestMetrics:
    # Produce genuine BacktestMetrics from Rust evaluate_backtest boundary
    pred = create_return_prediction(0.1, 0.08, 0.12, 0.95, ModelDescriptor("model", "1.0", "v1"))
    obs = BacktestObservation(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction=pred,
        actual_return=0.1,
    )
    return evaluate_backtest("fund1", [obs])


def test_immutability(
    mock_scope: HistoricalPredictionEvaluationScope, native_metrics: BacktestMetrics
) -> None:
    evaluation = HistoricalPredictionEvaluation(
        metrics=native_metrics,
        scope=mock_scope,
        total_period_count=1,
        evaluated_period_count=1,
        skipped_period_count=0,
        no_eligible_snapshots_count=0,
        insufficient_history_count=0,
        target_not_yet_available_count=0,
        missing_target_observation_count=0,
    )
    with pytest.raises(AttributeError):
        evaluation.evaluated_period_count = 2  # type: ignore


def test_strict_non_bool_int_counts(
    mock_scope: HistoricalPredictionEvaluationScope, native_metrics: BacktestMetrics
) -> None:
    with pytest.raises(
        InvalidHistoricalPredictionEvaluationError, match="must be a non-bool integer"
    ):
        HistoricalPredictionEvaluation(
            metrics=native_metrics,
            scope=mock_scope,
            total_period_count=True,  # type: ignore
            evaluated_period_count=1,
            skipped_period_count=0,
            no_eligible_snapshots_count=0,
            insufficient_history_count=0,
            target_not_yet_available_count=0,
            missing_target_observation_count=0,
        )


def test_non_negative_bounds(
    mock_scope: HistoricalPredictionEvaluationScope, native_metrics: BacktestMetrics
) -> None:
    with pytest.raises(InvalidHistoricalPredictionEvaluationError, match="must be non-negative"):
        HistoricalPredictionEvaluation(
            metrics=native_metrics,
            scope=mock_scope,
            total_period_count=1,
            evaluated_period_count=1,
            skipped_period_count=0,
            no_eligible_snapshots_count=-1,
            insufficient_history_count=1,
            target_not_yet_available_count=0,
            missing_target_observation_count=0,
        )


def test_count_arithmetic_sums_evaluated_skipped(
    mock_scope: HistoricalPredictionEvaluationScope, native_metrics: BacktestMetrics
) -> None:
    with pytest.raises(InvalidHistoricalPredictionEvaluationError, match="!= total"):
        HistoricalPredictionEvaluation(
            metrics=native_metrics,
            scope=mock_scope,
            total_period_count=3,
            evaluated_period_count=1,
            skipped_period_count=1,
            no_eligible_snapshots_count=1,
            insufficient_history_count=0,
            target_not_yet_available_count=0,
            missing_target_observation_count=0,
        )


def test_count_arithmetic_sums_skip_categories(
    mock_scope: HistoricalPredictionEvaluationScope, native_metrics: BacktestMetrics
) -> None:
    with pytest.raises(
        InvalidHistoricalPredictionEvaluationError,
        match="skip categories sum .* != skipped_period_count",
    ):
        HistoricalPredictionEvaluation(
            metrics=native_metrics,
            scope=mock_scope,
            total_period_count=2,
            evaluated_period_count=1,
            skipped_period_count=1,
            no_eligible_snapshots_count=0,
            insufficient_history_count=0,
            target_not_yet_available_count=0,
            missing_target_observation_count=0,
        )


def test_scope_presence_constraints(
    mock_scope: HistoricalPredictionEvaluationScope, native_metrics: BacktestMetrics
) -> None:
    # Empty evaluation must have scope=None
    with pytest.raises(
        InvalidHistoricalPredictionEvaluationError,
        match="scope must be None when total_period_count is 0",
    ):
        HistoricalPredictionEvaluation(
            metrics=None,
            scope=mock_scope,
            total_period_count=0,
            evaluated_period_count=0,
            skipped_period_count=0,
            no_eligible_snapshots_count=0,
            insufficient_history_count=0,
            target_not_yet_available_count=0,
            missing_target_observation_count=0,
        )

    # Non-empty evaluation must have scope!=None
    with pytest.raises(
        InvalidHistoricalPredictionEvaluationError,
        match="scope must be non-None when total_period_count > 0",
    ):
        HistoricalPredictionEvaluation(
            metrics=native_metrics,
            scope=None,
            total_period_count=1,
            evaluated_period_count=1,
            skipped_period_count=0,
            no_eligible_snapshots_count=0,
            insufficient_history_count=0,
            target_not_yet_available_count=0,
            missing_target_observation_count=0,
        )


def test_invalid_scope_type(native_metrics: BacktestMetrics) -> None:
    with pytest.raises(
        InvalidHistoricalPredictionEvaluationError,
        match="scope must be HistoricalPredictionEvaluationScope",
    ):
        HistoricalPredictionEvaluation(
            metrics=native_metrics,
            scope="invalid_scope",  # type: ignore
            total_period_count=1,
            evaluated_period_count=1,
            skipped_period_count=0,
            no_eligible_snapshots_count=0,
            insufficient_history_count=0,
            target_not_yet_available_count=0,
            missing_target_observation_count=0,
        )


def test_metrics_presence_constraints(
    mock_scope: HistoricalPredictionEvaluationScope, native_metrics: BacktestMetrics
) -> None:
    # Zero evaluated must have metrics=None
    with pytest.raises(
        InvalidHistoricalPredictionEvaluationError,
        match="metrics must be None when evaluated_period_count is 0",
    ):
        HistoricalPredictionEvaluation(
            metrics=native_metrics,
            scope=mock_scope,
            total_period_count=1,
            evaluated_period_count=0,
            skipped_period_count=1,
            no_eligible_snapshots_count=1,
            insufficient_history_count=0,
            target_not_yet_available_count=0,
            missing_target_observation_count=0,
        )

    # Non-zero evaluated must have metrics!=None
    with pytest.raises(
        InvalidHistoricalPredictionEvaluationError,
        match="metrics must be non-None when evaluated_period_count > 0",
    ):
        HistoricalPredictionEvaluation(
            metrics=None,
            scope=mock_scope,
            total_period_count=1,
            evaluated_period_count=1,
            skipped_period_count=0,
            no_eligible_snapshots_count=0,
            insufficient_history_count=0,
            target_not_yet_available_count=0,
            missing_target_observation_count=0,
        )


def test_native_metrics_type_check(
    mock_scope: HistoricalPredictionEvaluationScope,
) -> None:
    with pytest.raises(
        InvalidHistoricalPredictionEvaluationError, match="metrics must be BacktestMetrics"
    ):
        HistoricalPredictionEvaluation(
            metrics="invalid_metrics",  # type: ignore
            scope=mock_scope,
            total_period_count=1,
            evaluated_period_count=1,
            skipped_period_count=0,
            no_eligible_snapshots_count=0,
            insufficient_history_count=0,
            target_not_yet_available_count=0,
            missing_target_observation_count=0,
        )


def test_sample_count_mismatch(
    mock_scope: HistoricalPredictionEvaluationScope,
) -> None:
    # Generate native metrics with sample_count=1, but evaluation claims 2.
    pred = create_return_prediction(0.1, 0.08, 0.12, 0.95, ModelDescriptor("model", "1.0", "v1"))
    obs = BacktestObservation(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction=pred,
        actual_return=0.1,
    )
    native_metrics = evaluate_backtest("fund1", [obs])

    with pytest.raises(
        InvalidHistoricalPredictionEvaluationError,
        match="metrics.sample_count .* != evaluated_period_count",
    ):
        HistoricalPredictionEvaluation(
            metrics=native_metrics,
            scope=mock_scope,
            total_period_count=2,
            evaluated_period_count=2,
            skipped_period_count=0,
            no_eligible_snapshots_count=0,
            insufficient_history_count=0,
            target_not_yet_available_count=0,
            missing_target_observation_count=0,
        )
