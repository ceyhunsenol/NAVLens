"""Tests for FX-adjusted point-in-time fund-return reconciliation formatting."""

from datetime import UTC, datetime

from navlens import (
    AlignmentPolicy,
    AssetClass,
    CurrencyCode,
    CurrencyPair,
    FxRate,
    FxRateKind,
    FxRateObservation,
    FxReturnPolicy,
    HoldingPosition,
    HoldingSnapshot,
    MarketDate,
    PointInTimeAlignmentRequest,
    PriceAdjustment,
    PriceCurrencyPolicy,
    PriceObservation,
    ReturnPeriod,
    SecurityPriceObservation,
    SecurityPriceSnapshot,
    UnitPrice,
    align_point_in_time,
    calculate_point_in_time_fx_adjusted_return_contribution,
    calculate_price_period_returns,
    reconcile_fx_adjusted_fund_return,
)
from navlens.alignment import PointInTimeFxReturnContributionRequest
from navlens.datasets import FundUnitPriceSnapshot, FxRateSnapshot
from navlens.reconciliation import (
    PointInTimeFxFundReturnReconciliationResult,
    format_point_in_time_fx_adjusted_fund_return_reconciliation_result,
)


def _make_fx_alignment_and_contrib(
    weight: float = 1.0,
) -> tuple[ReturnPeriod, PointInTimeFxFundReturnReconciliationResult]:
    policy = AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("total_return_adjusted"),
        MarketDate(2026, 1, 31),
        2,
        5,
    ).with_price_currency_policy(PriceCurrencyPolicy("permit_foreign"))

    request = PointInTimeAlignmentRequest(
        "AAL",
        datetime(2026, 2, 1, 12, 0, tzinfo=UTC),
        "kap",
        "market",
        policy,
    )
    holdings = HoldingSnapshot(
        fund_id="AAL",
        effective_date=MarketDate(2026, 1, 31),
        published_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        source_id="kap",
        positions=(HoldingPosition("INST_A", AssetClass("equity"), weight),),
    )
    prices = [
        SecurityPriceSnapshot(
            observation=SecurityPriceObservation(
                "INST_A",
                MarketDate(2026, 1, 30),
                UnitPrice(100.0),
                CurrencyCode("USD"),
                PriceAdjustment("total_return_adjusted"),
            ),
            available_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            ingested_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            source_id="market",
        ),
        SecurityPriceSnapshot(
            observation=SecurityPriceObservation(
                "INST_A",
                MarketDate(2026, 1, 31),
                UnitPrice(110.0),
                CurrencyCode("USD"),
                PriceAdjustment("total_return_adjusted"),
            ),
            available_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            ingested_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            source_id="market",
        ),
    ]

    alignment_result = align_point_in_time(request, [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 30), MarketDate(2026, 1, 31))

    fx_request = PointInTimeFxReturnContributionRequest(
        alignment_result,
        period,
        "tcmb",
        FxReturnPolicy(FxRateKind("non_cash_buying"), 5),
    )
    fx_rates = [
        FxRateSnapshot(
            observation=FxRateObservation(
                CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY")),
                MarketDate(2026, 1, 30),
                FxRate(30.0),
                FxRateKind("non_cash_buying"),
            ),
            available_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            ingested_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            source_id="tcmb",
        ),
        FxRateSnapshot(
            observation=FxRateObservation(
                CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY")),
                MarketDate(2026, 1, 31),
                FxRate(31.0),
                FxRateKind("non_cash_buying"),
            ),
            available_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            ingested_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            source_id="tcmb",
        ),
    ]
    fx_contrib = calculate_point_in_time_fx_adjusted_return_contribution(fx_request, fx_rates)

    start_snap = FundUnitPriceSnapshot(
        fund_id="AAL",
        observation=PriceObservation(MarketDate(2026, 1, 30), UnitPrice(10.0)),
        available_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        source_id="tefas",
    )
    end_snap = FundUnitPriceSnapshot(
        fund_id="AAL",
        observation=PriceObservation(MarketDate(2026, 1, 31), UnitPrice(11.2)),
        available_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        source_id="tefas",
    )

    period_returns = calculate_price_period_returns(
        "AAL",
        [start_snap.observation, end_snap.observation],
    )
    recon_result = reconcile_fx_adjusted_fund_return(
        period_returns[0],
        fx_contrib.contribution_result,
    )

    result = PointInTimeFxFundReturnReconciliationResult(
        contribution=fx_contrib,
        start_snapshot=start_snap,
        end_snapshot=end_snap,
        reconciliation_result=recon_result,
        fund_price_source_id="tefas",
    )
    return period, result


def test_formats_fx_reconciliation_success_with_complete_coverage() -> None:
    _, result = _make_fx_alignment_and_contrib()
    formatted = format_point_in_time_fx_adjusted_fund_return_reconciliation_result(result)

    assert "FX-Adjusted Return Contribution Report" in formatted
    assert "Selected FX Snapshots Provenance:" in formatted
    assert "Fund Return Reconciliation" in formatted
    assert "Exact Period: 2026-01-30 to 2026-01-31" in formatted
    assert "Fund Price Source ID: tefas" in formatted
    assert "Published Fund Return (Decimal): 0.120000" in formatted
    assert "Observed Portfolio Contribution (Decimal): 0.136667" in formatted
    assert "Reconciliation Residual (Decimal): -0.016667" in formatted
    assert "WARNING" not in formatted


def test_formats_fx_reconciliation_incomplete_coverage_warning() -> None:
    _, result = _make_fx_alignment_and_contrib(weight=0.5)
    formatted = format_point_in_time_fx_adjusted_fund_return_reconciliation_result(result)

    assert (
        "WARNING: The observed portfolio contribution is incomplete (return coverage < 1.0)."
        in formatted
    )
    assert (
        "The reconciliation residual includes unobserved portfolio weight and must not be"
        in formatted
    )
