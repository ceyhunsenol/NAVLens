import pytest
from navlens import (
    MarketDate,
    NavlensValidationError,
    PeriodDecimalReturn,
    PriceObservation,
    UnitPrice,
    calculate_price_period_returns,
    calculate_price_returns,
)


def _obs(day: int, price: float) -> PriceObservation:
    return PriceObservation(MarketDate(2026, 1, day), UnitPrice(price))


def test_calculates_period_returns() -> None:
    observations = [
        _obs(2, 100.0),
        _obs(5, 101.0),
        _obs(6, 100.495),
    ]

    returns = calculate_price_period_returns("ABC", observations)

    assert len(returns) == 2
    assert all(isinstance(value, PeriodDecimalReturn) for value in returns)

    assert returns[0].period_start_date == MarketDate(2026, 1, 2)
    assert returns[0].period_end_date == MarketDate(2026, 1, 5)
    assert abs(returns[0].return_decimal - 0.01) < 1e-12

    assert returns[1].period_start_date == MarketDate(2026, 1, 5)
    assert returns[1].period_end_date == MarketDate(2026, 1, 6)
    assert abs(returns[1].return_decimal + 0.005) < 1e-12


def test_output_parity_with_calculate_price_returns() -> None:
    observations = [
        _obs(2, 100.0),
        _obs(5, 101.0),
        _obs(6, 100.495),
    ]

    period_returns = calculate_price_period_returns("ABC", observations)
    dated_returns = calculate_price_returns("ABC", observations)

    assert len(period_returns) == len(dated_returns)

    for period_ret, dated_ret in zip(period_returns, dated_returns, strict=True):
        assert period_ret.return_decimal == dated_ret.return_decimal
        assert period_ret.period_end_date == dated_ret.date


def test_rejects_fewer_than_two_observations() -> None:
    with pytest.raises(
        NavlensValidationError,
        match="at least two price observations are required; got 1",
    ):
        calculate_price_period_returns("ABC", [_obs(2, 100.0)])


def test_rejects_duplicate_dates() -> None:
    with pytest.raises(NavlensValidationError, match="duplicate unit price for"):
        calculate_price_period_returns(
            "ABC",
            [
                _obs(2, 100.0),
                _obs(2, 101.0),
            ],
        )


def test_rejects_decreasing_dates() -> None:
    with pytest.raises(NavlensValidationError, match="price dates must increase"):
        calculate_price_period_returns(
            "ABC",
            [
                _obs(5, 100.0),
                _obs(2, 101.0),
            ],
        )
