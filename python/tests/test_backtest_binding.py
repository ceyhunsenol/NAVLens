import pytest
from navlens import (
    BacktestObservation,
    MarketDate,
    ModelDescriptor,
    NavlensValidationError,
    create_return_prediction,
    evaluate_backtest,
)


def prediction(expected: float, confidence: float = 0.9):
    model = ModelDescriptor("ridge-baseline", "0.1.0", "market-v1")
    return create_return_prediction(
        expected,
        expected - 0.02,
        expected + 0.02,
        confidence,
        model,
    )


def test_evaluates_chronological_predictions_in_rust() -> None:
    observations = [
        BacktestObservation(
            MarketDate(2026, 1, 2),
            MarketDate(2026, 1, 5),
            prediction(0.01),
            0.02,
        ),
        BacktestObservation(
            MarketDate(2026, 1, 5),
            MarketDate(2026, 1, 6),
            prediction(-0.01),
            0.01,
        ),
    ]

    metrics = evaluate_backtest("AAL", observations)

    assert metrics.sample_count == 2
    assert metrics.mean_absolute_error == pytest.approx(0.015)
    assert metrics.mean_error == pytest.approx(-0.015)
    assert metrics.root_mean_squared_error == pytest.approx(0.0158113883)
    assert metrics.direction_accuracy == pytest.approx(0.5)
    assert metrics.interval is not None
    assert metrics.interval.confidence_level == pytest.approx(0.9)
    assert metrics.interval.sample_count == 2
    assert metrics.interval.coverage == pytest.approx(1.0)
    assert metrics.interval.mean_width == pytest.approx(0.04)


def test_rejects_prediction_on_target_date() -> None:
    date = MarketDate(2026, 1, 5)

    with pytest.raises(NavlensValidationError, match="must be earlier than target"):
        BacktestObservation(date, date, prediction(0.01), 0.02)


def test_rejects_empty_series() -> None:
    with pytest.raises(NavlensValidationError, match="at least one observation"):
        evaluate_backtest("AAL", [])


def test_rejects_mixed_interval_confidence_levels() -> None:
    observations = [
        BacktestObservation(
            MarketDate(2026, 1, 2),
            MarketDate(2026, 1, 5),
            prediction(0.01, 0.8),
            0.02,
        ),
        BacktestObservation(
            MarketDate(2026, 1, 5),
            MarketDate(2026, 1, 6),
            prediction(0.02, 0.9),
            0.01,
        ),
    ]

    with pytest.raises(NavlensValidationError, match="confidence level"):
        evaluate_backtest("AAL", observations)
