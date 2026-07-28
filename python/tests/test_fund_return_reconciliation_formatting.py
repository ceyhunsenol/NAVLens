"""Tests for point-in-time fund-return reconciliation formatting."""

from datetime import UTC, datetime

from navlens import (
    AlignmentPolicy,
    AssetClass,
    CurrencyCode,
    HoldingPosition,
    HoldingSnapshot,
    MarketDate,
    PointInTimeAlignmentRequest,
    PriceAdjustment,
    PriceObservation,
    ReturnPeriod,
    SecurityPriceObservation,
    SecurityPriceSnapshot,
    UnitPrice,
    align_point_in_time,
    calculate_point_in_time_return_contribution,
    calculate_price_period_returns,
    reconcile_fund_return,
)
from navlens.alignment import PointInTimeReturnContributionResult
from navlens.datasets import FundUnitPriceSnapshot
from navlens.reconciliation import (
    PointInTimeFundReturnReconciliationResult,
    format_point_in_time_fund_return_reconciliation_result,
)


def _make_alignment_and_contrib(
    weight: float = 1.0,
) -> tuple[
    PointInTimeAlignmentRequest,
    ReturnPeriod,
    PointInTimeReturnContributionResult,
]:
    policy = AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("total_return_adjusted"),
        MarketDate(2026, 1, 31),
        2,
        5,
    )
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
                CurrencyCode("TRY"),
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
                CurrencyCode("TRY"),
                PriceAdjustment("total_return_adjusted"),
            ),
            available_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            ingested_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            source_id="market",
        ),
    ]

    alignment_result = align_point_in_time(request, [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 30), MarketDate(2026, 1, 31))
    contrib = calculate_point_in_time_return_contribution(alignment_result, period)
    return request, period, contrib


def _make_fund_price(date: MarketDate, price: float) -> FundUnitPriceSnapshot:
    return FundUnitPriceSnapshot(
        fund_id="AAL",
        observation=PriceObservation(date, UnitPrice(price)),
        available_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        source_id="tefas",
    )


def test_formats_success_with_complete_coverage() -> None:
    _, period, contrib = _make_alignment_and_contrib()

    start_snap = _make_fund_price(MarketDate(2026, 1, 30), 10.0)
    end_snap = _make_fund_price(MarketDate(2026, 1, 31), 11.2)

    period_returns = calculate_price_period_returns(
        "AAL",
        [start_snap.observation, end_snap.observation],
    )

    recon_result = reconcile_fund_return(
        period_returns[0],
        contrib.contribution_result,
    )

    result = PointInTimeFundReturnReconciliationResult(
        contribution=contrib,
        start_snapshot=start_snap,
        end_snapshot=end_snap,
        reconciliation_result=recon_result,
        fund_price_source_id="tefas",
    )

    formatted = format_point_in_time_fund_return_reconciliation_result(result)

    assert "Fund Return Reconciliation" in formatted
    assert "Exact Period: 2026-01-30 to 2026-01-31" in formatted
    assert "Fund Price Source ID: tefas" in formatted

    assert "Start Snapshot:" in formatted
    assert "  Market Date: 2026-01-30" in formatted
    assert "  Unit Price: 10.000000" in formatted

    assert "End Snapshot:" in formatted
    assert "  Market Date: 2026-01-31" in formatted
    assert "  Unit Price: 11.200000" in formatted

    assert "Published Fund Return (Decimal): 0.120000" in formatted
    assert "Observed Portfolio Contribution (Decimal): 0.100000" in formatted
    assert "Return Coverage (Ratio): 1.000000" in formatted
    assert "Reconciliation Residual (Decimal): 0.020000" in formatted

    assert "WARNING" not in formatted

    lower = formatted.lower()
    assert "prediction error" not in lower
    assert "alpha" not in lower
    assert "fee" not in lower
    assert "expense" not in lower


def test_native_full_coverage_tolerance_controls_warning() -> None:
    _, _, contrib = _make_alignment_and_contrib(weight=1.0 - 5e-10)
    start_snap = _make_fund_price(MarketDate(2026, 1, 30), 10.0)
    end_snap = _make_fund_price(MarketDate(2026, 1, 31), 11.2)
    period_return = calculate_price_period_returns(
        "AAL",
        [start_snap.observation, end_snap.observation],
    )[0]
    recon_result = reconcile_fund_return(
        period_return,
        contrib.contribution_result,
    )
    result = PointInTimeFundReturnReconciliationResult(
        contribution=contrib,
        start_snapshot=start_snap,
        end_snapshot=end_snap,
        reconciliation_result=recon_result,
        fund_price_source_id="tefas",
    )

    formatted = format_point_in_time_fund_return_reconciliation_result(result)

    assert contrib.contribution_result.observed_contribution.has_full_coverage
    assert "WARNING" not in formatted


def test_incomplete_coverage_produces_warning() -> None:
    request, period, _ = _make_alignment_and_contrib()
    holdings = HoldingSnapshot(
        fund_id="AAL",
        effective_date=MarketDate(2026, 1, 31),
        published_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        source_id="kap",
        positions=(
            HoldingPosition("INST_A", AssetClass("equity"), 0.5),
            HoldingPosition("INST_B", AssetClass("equity"), 0.5),
        ),
    )
    prices = [
        SecurityPriceSnapshot(
            observation=SecurityPriceObservation(
                "INST_A",
                MarketDate(2026, 1, 30),
                UnitPrice(100.0),
                CurrencyCode("TRY"),
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
                CurrencyCode("TRY"),
                PriceAdjustment("total_return_adjusted"),
            ),
            available_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            ingested_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            source_id="market",
        ),
    ]

    alignment_result = align_point_in_time(request, [holdings], prices)
    contrib = calculate_point_in_time_return_contribution(alignment_result, period)

    start_snap = _make_fund_price(MarketDate(2026, 1, 30), 10.0)
    end_snap = _make_fund_price(MarketDate(2026, 1, 31), 11.2)

    period_returns = calculate_price_period_returns(
        "AAL",
        [start_snap.observation, end_snap.observation],
    )

    recon_result = reconcile_fund_return(
        period_returns[0],
        contrib.contribution_result,
    )

    result = PointInTimeFundReturnReconciliationResult(
        contribution=contrib,
        start_snapshot=start_snap,
        end_snapshot=end_snap,
        reconciliation_result=recon_result,
        fund_price_source_id="tefas",
    )

    formatted = format_point_in_time_fund_return_reconciliation_result(result)

    assert (
        "WARNING: The observed portfolio contribution is incomplete (return coverage < 1.0)."
        in formatted
    )
    assert (
        "The reconciliation residual includes unobserved portfolio weight and must not be"
        in formatted
    )
    assert "interpreted as a prediction error or alpha." in formatted
