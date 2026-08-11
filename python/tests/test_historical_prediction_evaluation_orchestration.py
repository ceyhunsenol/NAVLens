"""Orchestration tests for point-in-time historical prediction dataset evaluation."""

from datetime import UTC, datetime

import pytest
from navlens import (
    BacktestObservation,
    MarketDate,
    evaluate_backtest,
)
from navlens.prediction.historical import (
    HistoricalPredictionDataset,
    HistoricalPredictionEvaluationScope,
    UnsupportedHistoricalPredictionDatasetError,
    evaluate_historical_prediction_dataset,
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
def base_dataset(mock_scope: HistoricalPredictionEvaluationScope) -> HistoricalPredictionDataset:
    req = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        pricing_as_of_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
    )
    return make_real_historical_prediction_dataset((req,))


def test_empty_dataset_native_bypass(
    mock_scope: HistoricalPredictionEvaluationScope, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = HistoricalPredictionDataset(scope=mock_scope, outcomes=tuple())

    # Prove evaluate_backtest is never called
    called = False

    def mock_eval(*args: object, **kwargs: object) -> object:
        nonlocal called
        called = True
        return None

    monkeypatch.setattr("navlens.prediction.historical.evaluation.evaluate_backtest", mock_eval)

    result = evaluate_historical_prediction_dataset(dataset)
    assert not called
    assert result.metrics is None
    assert result.scope is None
    assert result.total_period_count == 0


def test_all_skipped_dataset_native_bypass_and_identity(
    mock_scope: HistoricalPredictionEvaluationScope,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Build dataset that skips due to no snapshots
    req = make_request()
    dataset = make_real_historical_prediction_dataset((req,), snapshots=[])

    # Prove evaluate_backtest is never called
    called = False

    def mock_eval(*args: object, **kwargs: object) -> object:
        nonlocal called
        called = True
        return None

    monkeypatch.setattr("navlens.prediction.historical.evaluation.evaluate_backtest", mock_eval)

    result = evaluate_historical_prediction_dataset(dataset)
    assert not called
    assert result.metrics is None
    # Preserve exact scope object identity
    assert result.scope is dataset.scope
    assert result.total_period_count == 1
    assert result.skipped_period_count == 1
    assert result.no_eligible_snapshots_count == 1


def test_single_success(
    base_dataset: HistoricalPredictionDataset, monkeypatch: pytest.MonkeyPatch
) -> None:
    called_count = 0
    captured_fund_id = None
    captured_obs = None
    real_evaluate_backtest = evaluate_backtest

    def spy_eval(fund_id: str, observations: tuple[BacktestObservation, ...]):
        nonlocal called_count, captured_fund_id, captured_obs
        called_count += 1
        captured_fund_id = fund_id
        captured_obs = observations
        return real_evaluate_backtest(fund_id, observations)

    monkeypatch.setattr("navlens.prediction.historical.evaluation.evaluate_backtest", spy_eval)

    result = evaluate_historical_prediction_dataset(base_dataset)

    assert result.metrics is not None
    assert result.metrics.sample_count == 1
    assert result.scope is base_dataset.scope
    assert result.evaluated_period_count == 1
    assert result.skipped_period_count == 0

    assert called_count == 1
    assert captured_fund_id == base_dataset.scope.fund_id
    assert captured_obs is not None
    assert len(captured_obs) == 1

    rec = base_dataset.outcomes[0]
    assert captured_obs[0].prediction_date == rec.request.prediction_date
    assert captured_obs[0].target_date == rec.request.target_date
    assert captured_obs[0].actual_return == rec.realized_period_return.return_decimal


def test_multiple_success_order_preservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, 0, tzinfo=UTC),
    )

    dataset = make_real_historical_prediction_dataset((req1, req2))

    called_count = 0
    captured_fund_id = None
    captured_obs = None
    real_evaluate_backtest = evaluate_backtest

    def spy_eval(fund_id: str, observations: tuple[BacktestObservation, ...]):
        nonlocal called_count, captured_fund_id, captured_obs
        called_count += 1
        captured_fund_id = fund_id
        captured_obs = observations
        return real_evaluate_backtest(fund_id, observations)

    monkeypatch.setattr("navlens.prediction.historical.evaluation.evaluate_backtest", spy_eval)

    result = evaluate_historical_prediction_dataset(dataset)

    assert result.metrics is not None
    assert result.metrics.sample_count == 2
    assert result.scope is dataset.scope

    assert called_count == 1
    assert captured_fund_id == dataset.scope.fund_id
    assert captured_obs is not None
    assert len(captured_obs) == 2

    # Verify ordering and typed properties
    rec1 = dataset.outcomes[0]
    rec2 = dataset.outcomes[1]

    assert captured_obs[0].prediction_date == rec1.request.prediction_date
    assert captured_obs[0].target_date == rec1.request.target_date
    assert captured_obs[0].actual_return == rec1.realized_period_return.return_decimal

    assert captured_obs[1].prediction_date == rec2.request.prediction_date
    assert captured_obs[1].target_date == rec2.request.target_date
    assert captured_obs[1].actual_return == rec2.realized_period_return.return_decimal


def test_unsupported_dataset_fails_fast() -> None:
    class DummyDataset:
        pass

    with pytest.raises(UnsupportedHistoricalPredictionDatasetError):
        evaluate_historical_prediction_dataset(DummyDataset())  # type: ignore
