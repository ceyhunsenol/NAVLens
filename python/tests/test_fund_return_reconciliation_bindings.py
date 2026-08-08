import pytest
from navlens import (
    AlignmentPolicy,
    AssetClass,
    CurrencyCode,
    CurrencyPair,
    FundReturnReconciliation,
    FundReturnReconciliationResult,
    FxAdjustedReturnContributionResult,
    FxRate,
    FxRateKind,
    FxRateObservation,
    FxRateSeries,
    FxReturnPolicy,
    HoldingPosition,
    MarketDate,
    NavlensValidationError,
    PeriodDecimalReturn,
    PriceAdjustment,
    PriceCurrencyPolicy,
    ReturnContributionResult,
    ReturnPeriod,
    SecurityPriceHistoryCandidate,
    SecurityPriceObservation,
    UnitPrice,
    align_holdings_prices,
    calculate_fx_adjusted_return_contribution,
    calculate_return_contribution,
    reconcile_fund_return,
    reconcile_fx_adjusted_fund_return,
)


def _create_valid_contribution(
    target_period: ReturnPeriod,
    *,
    end_price: float = 110.0,
    weight: float = 0.8,
) -> ReturnContributionResult:
    holdings = [HoldingPosition("AAPL", AssetClass("Equity"), weight)]
    prices = [
        SecurityPriceObservation(
            "AAPL",
            target_period.period_start_date,
            UnitPrice(100.0),
            CurrencyCode("USD"),
            PriceAdjustment("unadjusted"),
        ),
        SecurityPriceObservation(
            "AAPL",
            target_period.period_end_date,
            UnitPrice(end_price),
            CurrencyCode("USD"),
            PriceAdjustment("unadjusted"),
        ),
    ]
    candidates = [SecurityPriceHistoryCandidate("AAPL", prices)]
    policy = AlignmentPolicy(
        CurrencyCode("USD"),
        PriceAdjustment("unadjusted"),
        target_period.period_end_date,
        2,
        10,
    )
    report = align_holdings_prices(holdings, candidates, policy)
    return calculate_return_contribution(report, target_period)


def test_exact_period_success() -> None:
    start = MarketDate(2026, 1, 30)
    end = MarketDate(2026, 1, 31)
    period = ReturnPeriod(start, end)
    contribution = _create_valid_contribution(period)
    published = PeriodDecimalReturn(period, 0.12)

    result = reconcile_fund_return(published, contribution)

    assert result.period == period

    recon = result.reconciliation
    assert recon.published_fund_return == 0.12
    assert recon.observed_portfolio_contribution.observed_contribution == pytest.approx(0.08)
    assert recon.observed_portfolio_contribution.return_coverage == pytest.approx(0.8)
    assert recon.reconciliation_residual == pytest.approx(0.04)


def test_negative_residual() -> None:
    start = MarketDate(2026, 1, 30)
    end = MarketDate(2026, 1, 31)
    period = ReturnPeriod(start, end)
    contribution = _create_valid_contribution(period)
    published = PeriodDecimalReturn(period, 0.05)

    result = reconcile_fund_return(published, contribution)
    recon = result.reconciliation

    assert recon.published_fund_return == 0.05
    assert recon.observed_portfolio_contribution.observed_contribution == pytest.approx(0.08)
    assert recon.reconciliation_residual == pytest.approx(-0.03)


def test_period_mismatch() -> None:
    start1 = MarketDate(2026, 1, 30)
    end1 = MarketDate(2026, 1, 31)
    period1 = ReturnPeriod(start1, end1)

    start2 = MarketDate(2026, 1, 29)
    end2 = MarketDate(2026, 1, 31)
    period2 = ReturnPeriod(start2, end2)

    contribution = _create_valid_contribution(period2)
    published = PeriodDecimalReturn(period1, 0.12)

    with pytest.raises(NavlensValidationError) as exc_info:
        reconcile_fund_return(published, contribution)

    error_msg = str(exc_info.value)
    assert "fund return period" in error_msg
    assert "does not match portfolio contribution period" in error_msg
    assert "2026-01-30" in error_msg
    assert "2026-01-29" in error_msg


def test_core_non_finite_error_mapping() -> None:
    start = MarketDate(2026, 1, 30)
    end = MarketDate(2026, 1, 31)
    period = ReturnPeriod(start, end)

    holdings = [HoldingPosition("AAPL", AssetClass("Equity"), 1.0)]
    prices = [
        SecurityPriceObservation(
            "AAPL", start, UnitPrice(1e-154), CurrencyCode("USD"), PriceAdjustment("unadjusted")
        ),
        SecurityPriceObservation(
            "AAPL", end, UnitPrice(1e154), CurrencyCode("USD"), PriceAdjustment("unadjusted")
        ),
    ]
    candidates = [SecurityPriceHistoryCandidate("AAPL", prices)]
    policy = AlignmentPolicy(CurrencyCode("USD"), PriceAdjustment("unadjusted"), end, 2, 10)
    report = align_holdings_prices(holdings, candidates, policy)
    contribution = calculate_return_contribution(report, period)

    published = PeriodDecimalReturn(period, -1e308)

    with pytest.raises(NavlensValidationError) as exc_info:
        reconcile_fund_return(published, contribution)

    assert "domain validation failed" in str(exc_info.value)
    assert "number must be finite" in str(exc_info.value).lower()


def test_type_safety() -> None:
    start = MarketDate(2026, 1, 30)
    end = MarketDate(2026, 1, 31)
    period = ReturnPeriod(start, end)
    contribution = _create_valid_contribution(period)
    published = PeriodDecimalReturn(period, 0.12)

    with pytest.raises(TypeError):
        reconcile_fund_return(0.12, contribution)

    with pytest.raises(TypeError):
        reconcile_fund_return(published, "invalid_contribution")


def test_output_only_wrappers() -> None:
    with pytest.raises(TypeError):
        FundReturnReconciliation()

    with pytest.raises(TypeError):
        FundReturnReconciliationResult()


def test_determinism_parity() -> None:
    start = MarketDate(2026, 1, 30)
    end = MarketDate(2026, 1, 31)
    period = ReturnPeriod(start, end)
    contribution = _create_valid_contribution(period)
    published = PeriodDecimalReturn(period, 0.12)

    result1 = reconcile_fund_return(published, contribution)
    result2 = reconcile_fund_return(published, contribution)

    assert result1 == result2
    assert result1.reconciliation == result2.reconciliation
    assert result1.period == result2.period


def _create_valid_fx_contribution(
    target_period: ReturnPeriod,
    *,
    start_price: float = 100.0,
    end_price: float = 110.0,
    weight: float = 0.8,
    start_fx_rate: float = 30.0,
    end_fx_rate: float = 33.0,
) -> FxAdjustedReturnContributionResult:
    holdings = [HoldingPosition("AAPL", AssetClass("Equity"), weight)]
    prices = [
        SecurityPriceObservation(
            "AAPL",
            target_period.period_start_date,
            UnitPrice(start_price),
            CurrencyCode("USD"),
            PriceAdjustment("unadjusted"),
        ),
        SecurityPriceObservation(
            "AAPL",
            target_period.period_end_date,
            UnitPrice(end_price),
            CurrencyCode("USD"),
            PriceAdjustment("unadjusted"),
        ),
    ]
    candidates = [SecurityPriceHistoryCandidate("AAPL", prices)]
    policy = AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("unadjusted"),
        target_period.period_end_date,
        2,
        10,
    ).with_price_currency_policy(PriceCurrencyPolicy("permit_foreign"))
    report = align_holdings_prices(holdings, candidates, policy)
    fx_policy = FxReturnPolicy(FxRateKind("non_cash_buying"), 0)
    pair = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    fx_series = FxRateSeries(
        [
            FxRateObservation(
                pair,
                target_period.period_start_date,
                FxRate(start_fx_rate),
                fx_policy.required_fx_rate_kind,
            ),
            FxRateObservation(
                pair,
                target_period.period_end_date,
                FxRate(end_fx_rate),
                fx_policy.required_fx_rate_kind,
            ),
        ]
    )
    return calculate_fx_adjusted_return_contribution(report, target_period, [fx_series], fx_policy)


def test_fx_exact_period_success() -> None:
    start = MarketDate(2026, 1, 30)
    end = MarketDate(2026, 1, 31)
    period = ReturnPeriod(start, end)
    contribution = _create_valid_fx_contribution(period)
    published = PeriodDecimalReturn(period, 0.20)

    result = reconcile_fx_adjusted_fund_return(published, contribution)

    assert isinstance(result, FundReturnReconciliationResult)
    assert result.period == period

    recon = result.reconciliation
    assert recon.published_fund_return == 0.20
    assert recon.observed_portfolio_contribution.observed_contribution == pytest.approx(0.168)
    assert recon.observed_portfolio_contribution.return_coverage == pytest.approx(0.8)
    assert recon.reconciliation_residual == pytest.approx(0.032)


@pytest.mark.parametrize(
    ("published_return", "expected_residual"),
    [(0.20, 0.032), (0.10, -0.068), (0.168, 0.0)],
)
def test_fx_residual_signs(
    published_return: float,
    expected_residual: float,
) -> None:
    period = ReturnPeriod(MarketDate(2026, 1, 30), MarketDate(2026, 1, 31))
    contribution = _create_valid_fx_contribution(period)

    result = reconcile_fx_adjusted_fund_return(
        PeriodDecimalReturn(period, published_return), contribution
    )

    assert result.reconciliation.reconciliation_residual == pytest.approx(expected_residual)


def test_fx_period_mismatch_error_mapping() -> None:
    start1 = MarketDate(2026, 1, 30)
    end1 = MarketDate(2026, 1, 31)
    period1 = ReturnPeriod(start1, end1)

    start2 = MarketDate(2026, 1, 29)
    end2 = MarketDate(2026, 1, 31)
    period2 = ReturnPeriod(start2, end2)

    contribution = _create_valid_fx_contribution(period2)
    published = PeriodDecimalReturn(period1, 0.12)

    with pytest.raises(NavlensValidationError) as exc_info:
        reconcile_fx_adjusted_fund_return(published, contribution)

    error_msg = str(exc_info.value)
    assert "fund return period" in error_msg
    assert "does not match portfolio contribution period" in error_msg


def test_fx_core_non_finite_error_mapping() -> None:
    period = ReturnPeriod(MarketDate(2026, 1, 30), MarketDate(2026, 1, 31))
    contribution = _create_valid_fx_contribution(
        period,
        start_price=1e-154,
        end_price=1e154,
        weight=1.0,
        start_fx_rate=30.0,
        end_fx_rate=30.0,
    )

    with pytest.raises(NavlensValidationError) as exc_info:
        reconcile_fx_adjusted_fund_return(PeriodDecimalReturn(period, -1e308), contribution)

    assert "domain validation failed" in str(exc_info.value)
    assert "number must be finite" in str(exc_info.value).lower()


def test_legacy_and_fx_parity_bindings() -> None:
    start = MarketDate(2026, 1, 30)
    end = MarketDate(2026, 1, 31)
    period = ReturnPeriod(start, end)
    published = PeriodDecimalReturn(period, 0.12)

    legacy_contrib = _create_valid_contribution(period, end_price=150.0, weight=0.5)
    fx_contrib = _create_valid_fx_contribution(
        period,
        end_price=150.0,
        weight=0.5,
        end_fx_rate=30.0,
    )

    legacy_result = reconcile_fund_return(published, legacy_contrib)
    fx_result = reconcile_fx_adjusted_fund_return(published, fx_contrib)

    assert legacy_result == fx_result
    assert legacy_result.reconciliation == fx_result.reconciliation
