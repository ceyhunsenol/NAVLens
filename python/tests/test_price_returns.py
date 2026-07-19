from pathlib import Path

import pytest
from navlens import (
    MarketDate,
    NavlensValidationError,
    PriceObservation,
    UnitPrice,
    calculate_price_returns,
)
from navlens.sources.csv import read_price_records, to_price_observations


def fixture_observations(path: Path) -> list[PriceObservation]:
    return to_price_observations(read_price_records(path))


def test_matches_shared_rust_price_fixture(shared_price_csv_path: Path) -> None:
    returns = calculate_price_returns("ABC", fixture_observations(shared_price_csv_path))

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
