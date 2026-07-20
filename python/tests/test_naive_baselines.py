from pathlib import Path

import pandas as pd
import pytest
from navlens.evaluation import HistoricalMeanBaseline, LastReturnBaseline

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "daily_returns.csv"


@pytest.fixture
def daily_returns() -> pd.Series:
    frame = pd.read_csv(FIXTURE_PATH, parse_dates=["date"])
    return frame.set_index("date")["return_decimal"]


def test_historical_mean_predicts_expanding_average(daily_returns: pd.Series) -> None:
    history = daily_returns.iloc[:6]
    fitted = HistoricalMeanBaseline(6, "0.1.0", 0.8).fit_predict(history)

    assert fitted.prediction.expected_return == pytest.approx(history.mean())
    assert fitted.prediction.model.name == "historical-mean-baseline"
    assert fitted.prediction.model.feature_set_version == "historical-returns-mean-v1"
    assert fitted.training_end == history.index[-1]


def test_last_return_repeats_most_recent_observation(daily_returns: pd.Series) -> None:
    history = daily_returns.iloc[:6]
    fitted = LastReturnBaseline(6, "0.1.0", 0.8).fit_predict(history)

    assert fitted.prediction.expected_return == pytest.approx(history.iloc[-1])
    assert fitted.prediction.model.name == "last-return-baseline"
    assert fitted.prediction.model.feature_set_version == "last-return-v1"
    assert fitted.prediction.lower_bound <= fitted.prediction.expected_return
    assert fitted.prediction.expected_return <= fitted.prediction.upper_bound


@pytest.mark.parametrize("estimator_type", [HistoricalMeanBaseline, LastReturnBaseline])
def test_naive_baseline_requires_three_returns(estimator_type: type) -> None:
    with pytest.raises(ValueError, match="at least three"):
        estimator_type(2, "0.1.0")
