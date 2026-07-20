from pathlib import Path

import pandas as pd
import pytest
from navlens.evaluation import (
    HistoricalMeanBaseline,
    LastReturnBaseline,
    LinearBaselineWalkForward,
    compare_walk_forward,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "daily_returns.csv"


@pytest.fixture
def daily_returns() -> pd.Series:
    frame = pd.read_csv(FIXTURE_PATH, parse_dates=["date"])
    return frame.set_index("date")["return_decimal"]


def estimators() -> tuple:
    return (
        LinearBaselineWalkForward(lookback=3, model_version="0.1.0"),
        HistoricalMeanBaseline(initial_training_size=6, model_version="0.1.0"),
        LastReturnBaseline(initial_training_size=6, model_version="0.1.0"),
    )


def test_compares_models_on_identical_targets(daily_returns: pd.Series) -> None:
    comparison = compare_walk_forward("AAL", daily_returns, estimators())

    assert [entry.model_name for entry in comparison.entries] == [
        "linear-regression-baseline",
        "historical-mean-baseline",
        "last-return-baseline",
    ]
    target_sequences = [
        tuple(record.target_date for record in entry.result.records) for entry in comparison.entries
    ]
    assert target_sequences[1:] == target_sequences[:1] * 2
    assert all(entry.result.metrics.sample_count == 6 for entry in comparison.entries)


def test_first_predictions_cannot_see_future_returns(daily_returns: pd.Series) -> None:
    changed_future = daily_returns.copy()
    changed_future.iloc[6:] = changed_future.iloc[6:] * 100.0

    original = compare_walk_forward("AAL", daily_returns, estimators())
    changed = compare_walk_forward("AAL", changed_future, estimators())

    original_first = [entry.result.records[0] for entry in original.entries]
    changed_first = [entry.result.records[0] for entry in changed.entries]
    for before, after in zip(original_first, changed_first, strict=True):
        assert after.predicted_return == pytest.approx(before.predicted_return)
        assert after.lower_bound == pytest.approx(before.lower_bound)
        assert after.upper_bound == pytest.approx(before.upper_bound)


def test_rejects_different_initial_training_windows(daily_returns: pd.Series) -> None:
    mismatched = (
        HistoricalMeanBaseline(initial_training_size=6, model_version="0.1.0"),
        LastReturnBaseline(initial_training_size=7, model_version="0.1.0"),
    )

    with pytest.raises(ValueError, match="same initial training size"):
        compare_walk_forward("AAL", daily_returns, mismatched)
