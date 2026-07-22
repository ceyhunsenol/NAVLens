import pytest
from navlens import (
    CurrencyCode,
    MarketDate,
    NavlensValidationError,
    PriceAdjustment,
    SecurityPriceObservation,
    SecurityPriceSeries,
    UnitPrice,
)


def test_valid_currency_code() -> None:
    usd = CurrencyCode("USD")
    assert usd.code == "USD"
    assert str(usd) == "USD"
    assert repr(usd) == "CurrencyCode('USD')"
    assert usd == CurrencyCode("USD")


@pytest.mark.parametrize("invalid_code", ["usd", "US", "USDE", "US1", ""])
def test_invalid_currency_code(invalid_code: str) -> None:
    with pytest.raises(NavlensValidationError, match="currency"):
        CurrencyCode(invalid_code)


@pytest.mark.parametrize(
    ("input_val", "expected_name"),
    [
        ("unadjusted", "unadjusted"),
        ("UNADJUSTED", "unadjusted"),
        ("split_adjusted", "split_adjusted"),
        ("total_return_adjusted", "total_return_adjusted"),
    ],
)
def test_price_adjustment_variants(input_val: str, expected_name: str) -> None:
    adj = PriceAdjustment(input_val)
    assert adj.name == expected_name
    assert str(adj) == expected_name
    assert repr(adj) == f"PriceAdjustment('{expected_name}')"


def test_invalid_price_adjustment() -> None:
    with pytest.raises(NavlensValidationError, match="unknown price adjustment"):
        PriceAdjustment("invalid_variant")


def test_security_price_observation_preserves_fields() -> None:
    date = MarketDate(2026, 1, 15)
    price = UnitPrice(150.25)
    currency = CurrencyCode("USD")
    adjustment = PriceAdjustment("unadjusted")

    obs = SecurityPriceObservation("US67066G1040", date, price, currency, adjustment)

    assert obs.instrument_id == "US67066G1040"
    assert obs.market_date == date
    assert obs.price.value == price.value
    assert obs.currency == currency
    assert obs.adjustment == adjustment


def test_valid_security_price_series() -> None:
    currency = CurrencyCode("USD")
    adjustment = PriceAdjustment("unadjusted")
    obs1 = SecurityPriceObservation(
        "US67066G1040",
        MarketDate(2026, 1, 15),
        UnitPrice(150.25),
        currency,
        adjustment,
    )
    obs2 = SecurityPriceObservation(
        "US67066G1040",
        MarketDate(2026, 1, 16),
        UnitPrice(152.00),
        currency,
        adjustment,
    )

    series = SecurityPriceSeries([obs1, obs2])

    assert series.instrument_id == "US67066G1040"
    assert series.currency == currency
    assert series.adjustment == adjustment
    assert len(series) == 2
    assert series.observations == [obs1, obs2]


def test_rejects_insufficient_observations_for_series() -> None:
    obs = SecurityPriceObservation(
        "US67066G1040",
        MarketDate(2026, 1, 15),
        UnitPrice(150.25),
        CurrencyCode("USD"),
        PriceAdjustment("unadjusted"),
    )
    with pytest.raises(NavlensValidationError):
        SecurityPriceSeries([obs])


def test_rejects_non_chronological_dates_in_series() -> None:
    currency = CurrencyCode("USD")
    adj = PriceAdjustment("unadjusted")
    obs1 = SecurityPriceObservation(
        "US67066G1040", MarketDate(2026, 1, 16), UnitPrice(150.25), currency, adj
    )
    obs2 = SecurityPriceObservation(
        "US67066G1040", MarketDate(2026, 1, 15), UnitPrice(152.00), currency, adj
    )

    with pytest.raises(NavlensValidationError):
        SecurityPriceSeries([obs1, obs2])


def test_rejects_mixed_instruments_in_series() -> None:
    currency = CurrencyCode("USD")
    adj = PriceAdjustment("unadjusted")
    obs1 = SecurityPriceObservation(
        "US67066G1040", MarketDate(2026, 1, 15), UnitPrice(150.25), currency, adj
    )
    obs2 = SecurityPriceObservation(
        "US0378331005", MarketDate(2026, 1, 16), UnitPrice(152.00), currency, adj
    )

    with pytest.raises(NavlensValidationError, match="instrument ID"):
        SecurityPriceSeries([obs1, obs2])


def test_rejects_mixed_currencies_in_series() -> None:
    adj = PriceAdjustment("unadjusted")
    obs1 = SecurityPriceObservation(
        "US67066G1040",
        MarketDate(2026, 1, 15),
        UnitPrice(150.25),
        CurrencyCode("USD"),
        adj,
    )
    obs2 = SecurityPriceObservation(
        "US67066G1040",
        MarketDate(2026, 1, 16),
        UnitPrice(152.00),
        CurrencyCode("EUR"),
        adj,
    )

    with pytest.raises(NavlensValidationError, match="currency"):
        SecurityPriceSeries([obs1, obs2])


def test_rejects_mixed_adjustments_in_series() -> None:
    currency = CurrencyCode("USD")
    obs1 = SecurityPriceObservation(
        "US67066G1040",
        MarketDate(2026, 1, 15),
        UnitPrice(150.25),
        currency,
        PriceAdjustment("unadjusted"),
    )
    obs2 = SecurityPriceObservation(
        "US67066G1040",
        MarketDate(2026, 1, 16),
        UnitPrice(152.00),
        currency,
        PriceAdjustment("split_adjusted"),
    )

    with pytest.raises(NavlensValidationError, match="price adjustment"):
        SecurityPriceSeries([obs1, obs2])


def test_rejects_naked_values_in_observation_fields() -> None:
    date = MarketDate(2026, 1, 15)
    price = UnitPrice(150.25)
    currency = CurrencyCode("USD")
    adjustment = PriceAdjustment("unadjusted")

    # Naked str for date
    with pytest.raises(TypeError):
        SecurityPriceObservation("US67066G1040", "2026-01-15", price, currency, adjustment)  # type: ignore[arg-type]

    # Naked float for price
    with pytest.raises(TypeError):
        SecurityPriceObservation("US67066G1040", date, 150.25, currency, adjustment)  # type: ignore[arg-type]

    # Naked str for currency
    with pytest.raises(TypeError):
        SecurityPriceObservation("US67066G1040", date, price, "USD", adjustment)  # type: ignore[arg-type]

    # Naked str for adjustment
    with pytest.raises(TypeError):
        SecurityPriceObservation("US67066G1040", date, price, currency, "unadjusted")  # type: ignore[arg-type]
