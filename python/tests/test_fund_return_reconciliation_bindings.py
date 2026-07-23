import pytest
from navlens import (
    AlignmentPolicy,
    AssetClass,
    CurrencyCode,
    FundReturnReconciliation,
    FundReturnReconciliationResult,
    HoldingPosition,
    MarketDate,
    NavlensValidationError,
    PeriodDecimalReturn,
    PriceAdjustment,
    ReturnContributionResult,
    ReturnPeriod,
    SecurityPriceHistoryCandidate,
    SecurityPriceObservation,
    UnitPrice,
    align_holdings_prices,
    calculate_return_contribution,
    reconcile_fund_return,
)


def _create_valid_contribution(target_period: ReturnPeriod) -> ReturnContributionResult:
    holdings = [HoldingPosition("AAPL", AssetClass("Equity"), 0.8)]
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
            UnitPrice(110.0),
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
