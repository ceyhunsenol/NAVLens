import pytest
from navlens import (
    AlignmentPolicy,
    AssetClass,
    CurrencyCode,
    HoldingPosition,
    MarketDate,
    PriceAdjustment,
    ReturnPeriod,
    SecurityPriceHistoryCandidate,
    SecurityPriceObservation,
    UnitPrice,
    align_holdings_prices,
    calculate_return_contribution,
)


def policy() -> AlignmentPolicy:
    return AlignmentPolicy(
        fund_base_currency=CurrencyCode("TRY"),
        required_price_adjustment=PriceAdjustment("total_return_adjusted"),
        pricing_as_of_date=MarketDate(2023, 10, 15),
        minimum_observations=2,
        max_staleness_calendar_days=5,
    )


def candidate(
    instrument_id: str,
    prices: dict[int, float],
) -> SecurityPriceHistoryCandidate:
    observations = [
        SecurityPriceObservation(
            instrument_id,
            MarketDate(2023, 10, day),
            UnitPrice(price),
            CurrencyCode("TRY"),
            PriceAdjustment("total_return_adjusted"),
        )
        for day, price in prices.items()
    ]
    return SecurityPriceHistoryCandidate(instrument_id, observations)


def holding(instrument_id: str, weight: float) -> HoldingPosition:
    return HoldingPosition(instrument_id, AssetClass("equity"), weight)


def test_calculate_return_contribution_full_coverage() -> None:
    holdings = [holding("INST_A", 0.4), holding("INST_B", 0.6)]
    candidates = [
        candidate("INST_A", {10: 100.0, 15: 110.0}),
        candidate("INST_B", {10: 50.0, 15: 55.0}),
    ]

    report = align_holdings_prices(holdings, candidates, policy())
    period = ReturnPeriod(MarketDate(2023, 10, 10), MarketDate(2023, 10, 15))

    result = calculate_return_contribution(report, period)

    assert result.period == period
    assert result.price_coverage == pytest.approx(1.0)
    assert len(result.price_gaps) == 0
    assert len(result.return_gaps) == 0

    assert len(result.component_contributions) == 2
    contrib_a = result.component_contributions[0]
    assert contrib_a.holding.instrument_id == "INST_A"
    assert contrib_a.period_return.return_decimal == pytest.approx(0.1)
    assert contrib_a.contribution.market_return == pytest.approx(0.1)
    assert contrib_a.contribution.weighted_contribution == pytest.approx(0.04)

    contrib_b = result.component_contributions[1]
    assert contrib_b.holding.instrument_id == "INST_B"
    assert contrib_b.period_return.return_decimal == pytest.approx(0.1)
    assert contrib_b.contribution.market_return == pytest.approx(0.1)
    assert contrib_b.contribution.weighted_contribution == pytest.approx(0.06)

    assert result.observed_contribution.observed_contribution == pytest.approx(0.1)
    assert result.observed_contribution.return_coverage == pytest.approx(1.0)
    assert result.observed_contribution.has_full_coverage is True


def test_calculate_return_contribution_with_return_gaps() -> None:
    holdings = [holding("INST_A", 0.4), holding("INST_B", 0.6)]
    candidates = [
        candidate("INST_A", {10: 100.0, 15: 110.0}),
        candidate("INST_B", {11: 50.0, 15: 55.0}),
    ]

    report = align_holdings_prices(holdings, candidates, policy())
    period = ReturnPeriod(MarketDate(2023, 10, 10), MarketDate(2023, 10, 15))

    result = calculate_return_contribution(report, period)

    assert result.price_coverage == pytest.approx(1.0)
    assert len(result.price_gaps) == 0

    assert len(result.return_gaps) == 1
    assert result.return_gaps[0].holding.instrument_id == "INST_B"
    assert result.return_gaps[0].reason.kind == "missing_exact_period_return"

    assert len(result.component_contributions) == 1
    assert result.component_contributions[0].holding.instrument_id == "INST_A"
    assert result.component_contributions[0].contribution.weighted_contribution == pytest.approx(
        0.04
    )

    assert result.observed_contribution.observed_contribution == pytest.approx(0.04)
    assert result.observed_contribution.return_coverage == pytest.approx(0.4)
    assert result.observed_contribution.has_full_coverage is False


def test_calculate_return_contribution_with_price_gaps() -> None:
    holdings = [holding("INST_A", 0.4), holding("INST_B", 0.6)]
    candidates = [
        candidate("INST_A", {10: 100.0, 15: 110.0}),
    ]

    report = align_holdings_prices(holdings, candidates, policy())
    period = ReturnPeriod(MarketDate(2023, 10, 10), MarketDate(2023, 10, 15))

    result = calculate_return_contribution(report, period)

    assert result.price_coverage == pytest.approx(0.4)
    assert len(result.price_gaps) == 1
    assert result.price_gaps[0].holding.instrument_id == "INST_B"
    assert result.price_gaps[0].reason.kind == "missing_price_series"
    assert len(result.return_gaps) == 0

    assert len(result.component_contributions) == 1
    assert result.component_contributions[0].holding.instrument_id == "INST_A"

    assert result.observed_contribution.observed_contribution == pytest.approx(0.04)
    assert result.observed_contribution.return_coverage == pytest.approx(0.4)
    assert result.observed_contribution.has_full_coverage is False


def test_binding_rejects_non_wrapper_inputs() -> None:
    holdings = [holding("INST_A", 1.0)]
    candidates = [candidate("INST_A", {10: 100.0, 15: 110.0})]
    report = align_holdings_prices(holdings, candidates, policy())
    period = ReturnPeriod(MarketDate(2023, 10, 10), MarketDate(2023, 10, 15))

    with pytest.raises(TypeError):
        calculate_return_contribution("not-a-report", period)
    with pytest.raises(TypeError):
        calculate_return_contribution(report, "not-a-period")


def test_calculate_return_contribution_negative_return() -> None:
    holdings = [holding("INST_A", 0.4)]
    candidates = [candidate("INST_A", {10: 100.0, 15: 50.0})]

    report = align_holdings_prices(holdings, candidates, policy())
    period = ReturnPeriod(MarketDate(2023, 10, 10), MarketDate(2023, 10, 15))

    result = calculate_return_contribution(report, period)

    contrib_a = result.component_contributions[0]
    assert contrib_a.period_return.return_decimal == pytest.approx(-0.5)
    assert contrib_a.contribution.market_return == pytest.approx(-0.5)
    assert contrib_a.contribution.weighted_contribution == pytest.approx(-0.2)
    assert result.observed_contribution.observed_contribution == pytest.approx(-0.2)


def test_calculate_return_contribution_overflow_validation_error() -> None:
    from navlens import NavlensValidationError

    holdings = [holding("OVERFLOW", 1.0)]
    candidates = [candidate("OVERFLOW", {10: 1e-200, 15: 1e300})]

    report = align_holdings_prices(holdings, candidates, policy())
    period = ReturnPeriod(MarketDate(2023, 10, 10), MarketDate(2023, 10, 15))

    with pytest.raises(NavlensValidationError):
        calculate_return_contribution(report, period)


def test_calculate_return_contribution_preserves_input_order() -> None:
    holdings = [
        holding("PRICE_GAP_1", 0.1),
        holding("COVERED_1", 0.2),
        holding("RETURN_GAP_1", 0.1),
        holding("PRICE_GAP_2", 0.1),
        holding("COVERED_2", 0.2),
        holding("RETURN_GAP_2", 0.1),
    ]

    candidates = [
        candidate("COVERED_1", {10: 100.0, 15: 110.0}),
        candidate("RETURN_GAP_1", {11: 100.0, 15: 110.0}),
        candidate("COVERED_2", {10: 100.0, 15: 120.0}),
        candidate("RETURN_GAP_2", {11: 100.0, 15: 120.0}),
    ]

    report = align_holdings_prices(holdings, candidates, policy())
    period = ReturnPeriod(MarketDate(2023, 10, 10), MarketDate(2023, 10, 15))

    result = calculate_return_contribution(report, period)

    assert [c.holding.instrument_id for c in result.component_contributions] == [
        "COVERED_1",
        "COVERED_2",
    ]

    assert [g.holding.instrument_id for g in result.price_gaps] == [
        "PRICE_GAP_1",
        "PRICE_GAP_2",
    ]

    assert [g.holding.instrument_id for g in result.return_gaps] == [
        "RETURN_GAP_1",
        "RETURN_GAP_2",
    ]
