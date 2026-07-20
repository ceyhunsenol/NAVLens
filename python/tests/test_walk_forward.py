from pathlib import Path

import pandas as pd
import pytest
from navlens.evaluation import LinearBaselineWalkForward, run_walk_forward

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "daily_returns.csv"


@pytest.fixture
def daily_returns() -> pd.Series:
    frame = pd.read_csv(FIXTURE_PATH, parse_dates=["date"])
    return frame.set_index("date")["return_decimal"]


def evaluator() -> LinearBaselineWalkForward:
    return LinearBaselineWalkForward(
        lookback=3,
        model_version="0.1.0",
        confidence_level=0.8,
    )


def test_runs_expanding_window_backtest_through_rust(daily_returns: pd.Series) -> None:
    result = run_walk_forward("AAL", daily_returns, evaluator())

    assert len(result.records) == 6
    assert result.metrics.sample_count == len(result.records)
    assert result.records[0].prediction_date == daily_returns.index[5]
    assert result.records[0].target_date == daily_returns.index[6]
    assert result.records[-1].target_date == daily_returns.index[-1]
    assert result.records[0].model_name == "linear-regression-baseline"
    assert result.records[0].feature_schema_version == "lagged-returns-v1"
    assert all(record.training_end == record.prediction_date for record in result.records)
    assert result.metrics.interval is not None
    assert result.metrics.interval.sample_count == len(result.records)


def test_first_prediction_cannot_see_target_or_later_returns(
    daily_returns: pd.Series,
) -> None:
    changed_future = daily_returns.copy()
    changed_future.iloc[6:] = changed_future.iloc[6:] * 100.0

    original = run_walk_forward("AAL", daily_returns, evaluator())
    changed = run_walk_forward("AAL", changed_future, evaluator())

    assert changed.records[0].predicted_return == pytest.approx(
        original.records[0].predicted_return
    )
    assert changed.records[0].lower_bound == pytest.approx(original.records[0].lower_bound)
    assert changed.records[0].upper_bound == pytest.approx(original.records[0].upper_bound)


def test_rejects_training_window_too_short_for_baseline() -> None:
    with pytest.raises(ValueError, match="must be at least 6"):
        LinearBaselineWalkForward(
            lookback=3,
            model_version="0.1.0",
            minimum_training_returns=5,
        )


def test_requires_one_out_of_sample_target(daily_returns: pd.Series) -> None:
    short_returns = daily_returns.iloc[:6]

    with pytest.raises(ValueError, match="at least 7 returns"):
        run_walk_forward("AAL", short_returns, evaluator())
