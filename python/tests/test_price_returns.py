from pathlib import Path

import pandas as pd
import pytest
from navlens import (
    MarketDate,
    NavlensValidationError,
    PriceObservation,
    UnitPrice,
    calculate_price_returns,
)
from navlens.estimators import predict_next_return
from navlens.training import train_linear_baseline

FIXTURE_PATH = (
    Path(__file__).parents[2]
    / "crates"
    / "navlens-calendar"
    / "tests"
    / "fixtures"
    / "prices.csv"
)


def fixture_observations() -> list[PriceObservation]:
    frame = pd.read_csv(FIXTURE_PATH, parse_dates=["date"])
    return [
        PriceObservation(
            MarketDate(row.date.year, row.date.month, row.date.day),
            UnitPrice(row.unit_price),
        )
        for row in frame.itertuples(index=False)
    ]


def test_matches_shared_rust_price_fixture() -> None:
    returns = calculate_price_returns("ABC", fixture_observations())

    assert [value.return_decimal for value in returns] == pytest.approx(
        [0.01, -0.005, 0.015, -0.002, 0.01]
    )
    assert str(returns[0].date) == "2026-01-05"


def test_rejects_invalid_prices_and_duplicate_dates() -> None:
    with pytest.raises(NavlensValidationError, match="strictly positive"):
        UnitPrice(0.0)

    repeated = PriceObservation(MarketDate(2026, 1, 2), UnitPrice(100.0))
    with pytest.raises(NavlensValidationError, match="duplicate"):
        calculate_price_returns("ABC", [repeated, repeated])


def test_native_returns_feed_the_python_baseline() -> None:
    native_returns = calculate_price_returns("ABC", fixture_observations())
    returns = pd.Series(
        [value.return_decimal for value in native_returns],
        index=pd.to_datetime([str(value.date) for value in native_returns]),
    )
    artifact = train_linear_baseline(
        returns,
        lookback=1,
        model_version="0.1.0",
        confidence_level=0.80,
    )

    prediction = predict_next_return(artifact, returns)

    assert prediction.lower_bound <= prediction.expected_return <= prediction.upper_bound
    assert prediction.model.feature_set_version == "lagged-returns-v1"
