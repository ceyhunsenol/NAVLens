from pathlib import Path

import pandas as pd
import pytest
from navlens.estimators import predict_next_return
from navlens.features import build_lagged_return_dataset
from navlens.training import train_linear_baseline

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "daily_returns.csv"


@pytest.fixture
def daily_returns() -> pd.Series:
    frame = pd.read_csv(FIXTURE_PATH, parse_dates=["date"])
    return frame.set_index("date")["return_decimal"]


def test_feature_rows_never_include_their_target(daily_returns: pd.Series) -> None:
    dataset = build_lagged_return_dataset(daily_returns, lookback=3)

    first_target_date = dataset.targets.index[0]
    assert first_target_date == daily_returns.index[3]
    assert dataset.features.iloc[0].tolist() == [
        daily_returns.iloc[2],
        daily_returns.iloc[1],
        daily_returns.iloc[0],
    ]
    assert daily_returns.loc[first_target_date] not in dataset.features.iloc[0].tolist()


def test_rejects_non_chronological_returns(daily_returns: pd.Series) -> None:
    descending = daily_returns.sort_index(ascending=False)

    with pytest.raises(ValueError, match="chronological"):
        build_lagged_return_dataset(descending, lookback=3)


def test_trains_an_auditable_artifact(daily_returns: pd.Series) -> None:
    artifact = train_linear_baseline(
        daily_returns,
        lookback=3,
        model_version="0.1.0",
        confidence_level=0.80,
    )

    assert artifact.feature_schema_version == "lagged-returns-v1"
    assert artifact.target_definition == "next_published_nav_return_decimal"
    assert artifact.training_end == daily_returns.index[-1]
    assert set(artifact.evaluation_metrics) == {
        "linear_train_mae",
        "linear_train_rmse",
        "mean_dummy_train_mae",
        "mean_dummy_train_rmse",
    }
    assert (
        artifact.evaluation_metrics["linear_train_mae"]
        <= artifact.evaluation_metrics["mean_dummy_train_mae"]
    )


def test_prediction_is_validated_by_rust(daily_returns: pd.Series) -> None:
    artifact = train_linear_baseline(
        daily_returns,
        lookback=3,
        model_version="0.1.0",
        confidence_level=0.80,
    )

    prediction = predict_next_return(artifact, daily_returns)
    repeated_prediction = predict_next_return(artifact, daily_returns)

    assert prediction.lower_bound <= prediction.expected_return <= prediction.upper_bound
    assert repeated_prediction.expected_return == pytest.approx(prediction.expected_return)
    assert prediction.confidence_level == pytest.approx(0.80)
    assert prediction.model.name == "linear-regression-baseline"
    assert prediction.model.feature_set_version == "lagged-returns-v1"
