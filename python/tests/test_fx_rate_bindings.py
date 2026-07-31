import math

import pytest
from navlens import (
    CurrencyCode,
    CurrencyPair,
    FxRate,
    FxRateKind,
    FxRateObservation,
    FxRateSeries,
    MarketDate,
    NavlensValidationError,
)


def test_currency_pair_construction_and_getters() -> None:
    usd = CurrencyCode("USD")
    try_code = CurrencyCode("TRY")
    pair = CurrencyPair(usd, try_code)

    assert pair.base_currency == usd
    assert pair.quote_currency == try_code
    assert str(pair.base_currency) == "USD"
    assert str(pair.quote_currency) == "TRY"
    assert (
        repr(pair)
        == "CurrencyPair(base_currency=CurrencyCode('USD'), quote_currency=CurrencyCode('TRY'))"
    )
    assert pair == CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))


def test_currency_pair_rejects_identical_currencies() -> None:
    usd = CurrencyCode("USD")
    with pytest.raises(NavlensValidationError, match="identical"):
        CurrencyPair(usd, usd)


def test_currency_pair_rejects_naked_strings() -> None:
    usd = CurrencyCode("USD")
    with pytest.raises(TypeError):
        CurrencyPair("USD", usd)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        CurrencyPair(usd, "TRY")  # type: ignore[arg-type]


def test_fx_rate_construction_and_getters() -> None:
    rate = FxRate(35.25)
    assert rate.quote_currency_per_one_base_currency == 35.25
    assert repr(rate) == "FxRate(35.25)"
    assert rate == FxRate(35.25)


@pytest.mark.parametrize("invalid_rate", [0.0, -1.0, -35.25, math.nan, math.inf, -math.inf])
def test_fx_rate_rejects_invalid_values(invalid_rate: float) -> None:
    with pytest.raises(NavlensValidationError):
        FxRate(invalid_rate)


@pytest.mark.parametrize(
    ("input_val", "expected_name"),
    [
        ("non_cash_buying", "non_cash_buying"),
        ("NON_CASH_BUYING", "non_cash_buying"),
        ("non_cash_selling", "non_cash_selling"),
        ("cash_buying", "cash_buying"),
        ("cash_selling", "cash_selling"),
    ],
)
def test_fx_rate_kind_variants(input_val: str, expected_name: str) -> None:
    kind = FxRateKind(input_val)
    assert kind.name == expected_name
    assert str(kind) == expected_name
    assert repr(kind) == f"FxRateKind('{expected_name}')"
    assert kind == FxRateKind(expected_name)


def test_fx_rate_kind_rejects_unknown_kind() -> None:
    with pytest.raises(NavlensValidationError, match="unknown FX rate kind"):
        FxRateKind("unknown_kind")


def test_fx_rate_observation_construction_and_getters() -> None:
    pair = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    date = MarketDate(2026, 1, 15)
    rate = FxRate(35.25)
    kind = FxRateKind("non_cash_buying")

    obs = FxRateObservation(pair, date, rate, kind)

    assert obs.pair == pair
    assert obs.market_date == date
    assert obs.rate == rate
    assert obs.kind == kind


def test_fx_rate_observation_rejects_naked_values() -> None:
    pair = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    date = MarketDate(2026, 1, 15)
    rate = FxRate(35.25)
    kind = FxRateKind("non_cash_buying")

    with pytest.raises(TypeError):
        FxRateObservation("USD/TRY", date, rate, kind)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        FxRateObservation(pair, "2026-01-15", rate, kind)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        FxRateObservation(pair, date, 35.25, kind)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        FxRateObservation(pair, date, rate, "non_cash_buying")  # type: ignore[arg-type]


def test_fx_rate_series_singleton_and_multi_observation() -> None:
    pair = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")
    obs1 = FxRateObservation(pair, MarketDate(2026, 1, 15), FxRate(35.25), kind)
    obs2 = FxRateObservation(pair, MarketDate(2026, 1, 16), FxRate(35.50), kind)

    singleton = FxRateSeries([obs1])
    assert singleton.pair == pair
    assert singleton.kind == kind
    assert len(singleton) == 1
    assert singleton.observations == [obs1]

    multi = FxRateSeries([obs1, obs2])
    assert multi.pair == pair
    assert multi.kind == kind
    assert len(multi) == 2
    assert multi.observations == [obs1, obs2]


def test_fx_rate_series_rejects_empty() -> None:
    with pytest.raises(NavlensValidationError, match="empty"):
        FxRateSeries([])


def test_fx_rate_series_rejects_duplicate_dates() -> None:
    pair = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")
    obs1 = FxRateObservation(pair, MarketDate(2026, 1, 15), FxRate(35.25), kind)
    obs2 = FxRateObservation(pair, MarketDate(2026, 1, 15), FxRate(35.30), kind)

    with pytest.raises(NavlensValidationError, match="duplicate"):
        FxRateSeries([obs1, obs2])


def test_fx_rate_series_rejects_decreasing_dates() -> None:
    pair = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")
    obs1 = FxRateObservation(pair, MarketDate(2026, 1, 16), FxRate(35.25), kind)
    obs2 = FxRateObservation(pair, MarketDate(2026, 1, 15), FxRate(35.30), kind)

    with pytest.raises(NavlensValidationError, match="increase"):
        FxRateSeries([obs1, obs2])


def test_fx_rate_series_rejects_mixed_pairs() -> None:
    pair1 = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    pair2 = CurrencyPair(CurrencyCode("EUR"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")
    obs1 = FxRateObservation(pair1, MarketDate(2026, 1, 15), FxRate(35.25), kind)
    obs2 = FxRateObservation(pair2, MarketDate(2026, 1, 16), FxRate(38.10), kind)

    with pytest.raises(NavlensValidationError, match="currency pair"):
        FxRateSeries([obs1, obs2])


def test_fx_rate_series_rejects_mixed_kinds() -> None:
    pair = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    obs1 = FxRateObservation(
        pair, MarketDate(2026, 1, 15), FxRate(35.25), FxRateKind("non_cash_buying")
    )
    obs2 = FxRateObservation(
        pair, MarketDate(2026, 1, 16), FxRate(35.30), FxRateKind("cash_buying")
    )

    with pytest.raises(NavlensValidationError, match="rate kind"):
        FxRateSeries([obs1, obs2])
