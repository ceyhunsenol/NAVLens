"""Tests for Rust reconciliation metrics bindings."""

import pytest
from navlens import (
    AlignmentPolicy,
    AssetClass,
    CurrencyCode,
    HoldingPosition,
    MarketDate,
    NavlensValidationError,
    PeriodDecimalReturn,
    PriceAdjustment,
    ReconciliationMetrics,
    ReturnPeriod,
    SecurityPriceHistoryCandidate,
    SecurityPriceObservation,
    UnitPrice,
    align_holdings_prices,
    calculate_return_contribution,
    evaluate_reconciliation_metrics,
    reconcile_fund_return,
)


def _make_reconciliation(
    start_day: int,
    end_day: int,
    published_return: float,
    end_price: float,
    weight: float = 1.0,
):
    start_date = MarketDate(2026, 1, start_day)
    end_date = MarketDate(2026, 1, end_day)
    period = ReturnPeriod(start_date, end_date)
    holdings = [HoldingPosition("INST_A", AssetClass("equity"), weight)]
    prices = [
        SecurityPriceObservation(
            "INST_A",
            start_date,
            UnitPrice(100.0),
            CurrencyCode("USD"),
            PriceAdjustment("unadjusted"),
        ),
        SecurityPriceObservation(
            "INST_A",
            end_date,
            UnitPrice(end_price),
            CurrencyCode("USD"),
            PriceAdjustment("unadjusted"),
        ),
    ]
    candidates = [SecurityPriceHistoryCandidate("INST_A", prices)]
    policy = AlignmentPolicy(
        CurrencyCode("USD"),
        PriceAdjustment("unadjusted"),
        end_date,
        2,
        10,
    )
    report = align_holdings_prices(holdings, candidates, policy)
    contrib = calculate_return_contribution(report, period)
    published = PeriodDecimalReturn(period, published_return)
    return reconcile_fund_return(published, contrib)


def test_evaluates_typed_reconciliation_metrics_with_exact_getters() -> None:
    res1 = _make_reconciliation(1, 2, 0.10, 108.0, 1.0)  # residual = +0.02, cov = 1.0
    res2 = _make_reconciliation(2, 3, 0.05, 118.0, 0.5)  # residual = -0.04, cov = 0.5
    res3 = _make_reconciliation(3, 4, 0.03, 103.0, 1.0)  # residual = 0.00, cov = 1.0

    results = [res1, res2, res3]
    metrics = evaluate_reconciliation_metrics(results)

    assert isinstance(metrics, ReconciliationMetrics)
    assert metrics.sample_count == 3
    assert metrics.mean_absolute_residual == pytest.approx(0.02)
    assert metrics.mean_residual == pytest.approx(-0.02 / 3.0)
    assert metrics.root_mean_squared_residual == pytest.approx((0.0020 / 3.0) ** 0.5)
    assert metrics.mean_return_coverage == pytest.approx(2.5 / 3.0)
    assert metrics.full_return_coverage_ratio == pytest.approx(2.0 / 3.0)


def test_rejects_empty_reconciliation_results_list() -> None:
    with pytest.raises(
        NavlensValidationError,
        match="reconciliation metrics require at least one observation",
    ):
        evaluate_reconciliation_metrics([])


def test_rejects_duplicate_or_non_increasing_periods() -> None:
    res1 = _make_reconciliation(1, 2, 0.10, 108.0)
    res_dup = _make_reconciliation(1, 2, 0.10, 108.0)

    with pytest.raises(NavlensValidationError, match="duplicate reconciliation period"):
        evaluate_reconciliation_metrics([res1, res_dup])

    # End date 3 follows end date 3 (non-increasing)
    res_long = _make_reconciliation(1, 3, 0.10, 108.0)
    res_short = _make_reconciliation(2, 3, 0.05, 103.0)

    with pytest.raises(NavlensValidationError, match="chronological"):
        evaluate_reconciliation_metrics([res_long, res_short])

    res_middle = _make_reconciliation(2, 3, 0.05, 103.0)
    with pytest.raises(NavlensValidationError, match="duplicate reconciliation period"):
        evaluate_reconciliation_metrics([res1, res_middle, res_dup])


def test_evaluation_is_deterministic_and_preserves_inputs() -> None:
    res1 = _make_reconciliation(1, 2, 0.10, 108.0)
    res2 = _make_reconciliation(2, 3, 0.05, 103.0)
    results = [res1, res2]

    metrics1 = evaluate_reconciliation_metrics(results)
    metrics2 = evaluate_reconciliation_metrics(results)

    assert metrics1.sample_count == metrics2.sample_count
    assert metrics1.mean_absolute_residual == metrics2.mean_absolute_residual
    assert metrics1.mean_residual == metrics2.mean_residual
    assert metrics1.root_mean_squared_residual == metrics2.root_mean_squared_residual

    # Verify input objects remain unchanged
    assert res1.period == ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    assert res2.period == ReturnPeriod(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3))
