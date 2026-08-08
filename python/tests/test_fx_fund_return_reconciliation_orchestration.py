from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
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
    InvalidFundPriceSourceError,
    MarketDate,
    MissingExactFundUnitPriceSnapshotError,
    PointInTimeAlignmentRequest,
    PointInTimeFxAdjustedReturnContributionResult,
    PointInTimeFxFundReturnReconciliationResult,
    PointInTimeFxReturnContributionRequest,
    PriceAdjustment,
    PriceCurrencyPolicy,
    PriceObservation,
    ReturnPeriod,
    SecurityPriceObservation,
    SecurityPriceSnapshot,
    UnexpectedNativeReturnCardinalityError,
    UnitPrice,
    align_point_in_time,
    calculate_point_in_time_fx_adjusted_return_contribution,
    calculate_point_in_time_return_contribution,
    reconcile_point_in_time_fund_return,
    reconcile_point_in_time_fx_adjusted_fund_return,
)
from navlens.datasets import FundUnitPriceSnapshot, FxRateSnapshot

PERIOD_START = MarketDate(2026, 1, 30)
PERIOD_END = MarketDate(2026, 1, 31)
PREDICTION_TIMESTAMP = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
PUBLICATION_TIMESTAMP = datetime(2026, 2, 1, 10, 0, tzinfo=UTC)


def _fx_adjusted_contribution(
    *,
    start_fx_rate: float = 30.0,
    end_fx_rate: float = 31.0,
) -> PointInTimeFxAdjustedReturnContributionResult:
    policy = AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("total_return_adjusted"),
        PERIOD_END,
        2,
        5,
    ).with_price_currency_policy(PriceCurrencyPolicy("permit_foreign"))

    alignment_request = PointInTimeAlignmentRequest(
        "AAL",
        PREDICTION_TIMESTAMP,
        "kap",
        "market",
        policy,
    )
    holding = HoldingPosition("EQUITY", AssetClass("equity"), 1.0)
    holdings = HoldingSnapshot(
        fund_id="AAL",
        effective_date=PERIOD_END,
        published_at=PUBLICATION_TIMESTAMP,
        ingested_at=PUBLICATION_TIMESTAMP,
        source_id="kap",
        positions=(holding,),
    )
    security_prices = [
        _security_price(PERIOD_START, 100.0, "USD"),
        _security_price(PERIOD_END, 110.0, "USD"),
    ]
    alignment = align_point_in_time(alignment_request, [holdings], security_prices)

    fx_request = PointInTimeFxReturnContributionRequest(
        alignment,
        ReturnPeriod(PERIOD_START, PERIOD_END),
        "tcmb",
        FxReturnPolicy(FxRateKind("non_cash_buying"), 5),
    )
    fx_rates = [
        _fx_rate(PERIOD_START, start_fx_rate),
        _fx_rate(PERIOD_END, end_fx_rate),
    ]

    return calculate_point_in_time_fx_adjusted_return_contribution(fx_request, fx_rates)


def _security_price(market_date: MarketDate, price: float, currency: str) -> SecurityPriceSnapshot:
    return SecurityPriceSnapshot(
        observation=SecurityPriceObservation(
            "EQUITY",
            market_date,
            UnitPrice(price),
            CurrencyCode(currency),
            PriceAdjustment("total_return_adjusted"),
        ),
        available_at=PUBLICATION_TIMESTAMP,
        ingested_at=PUBLICATION_TIMESTAMP,
        source_id="market",
    )


def _fx_rate(market_date: MarketDate, rate: float) -> FxRateSnapshot:
    return FxRateSnapshot(
        observation=FxRateObservation(
            CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY")),
            market_date,
            FxRate(rate),
            FxRateKind("non_cash_buying"),
        ),
        available_at=PUBLICATION_TIMESTAMP,
        ingested_at=PUBLICATION_TIMESTAMP,
        source_id="tcmb",
    )


def _fund_price(
    market_date: MarketDate,
    price: float,
    *,
    fund_id: str = "AAL",
    source_id: str = "tefas",
    available_at: datetime = PUBLICATION_TIMESTAMP,
) -> FundUnitPriceSnapshot:
    return FundUnitPriceSnapshot(
        fund_id=fund_id,
        observation=PriceObservation(market_date, UnitPrice(price)),
        available_at=available_at,
        ingested_at=available_at,
        source_id=source_id,
    )


def _exact_prices() -> tuple[FundUnitPriceSnapshot, FundUnitPriceSnapshot]:
    return (
        _fund_price(PERIOD_START, 200.0),
        _fund_price(PERIOD_END, 224.0),
    )


def test_reconciles_exact_period_and_preserves_provenance() -> None:
    contribution = _fx_adjusted_contribution()
    start_snapshot, end_snapshot = _exact_prices()

    result = reconcile_point_in_time_fx_adjusted_fund_return(
        contribution,
        [start_snapshot, end_snapshot],
        fund_price_source_id="tefas",
    )

    assert isinstance(result, PointInTimeFxFundReturnReconciliationResult)
    assert result.contribution is contribution
    assert result.start_snapshot is start_snapshot
    assert result.end_snapshot is end_snapshot
    assert result.fund_price_source_id == "tefas"
    reconciliation = result.reconciliation_result.reconciliation
    assert reconciliation.published_fund_return == pytest.approx(0.12)
    # 1.1 * (31/30) - 1 = 0.1366666...
    assert reconciliation.observed_portfolio_contribution.observed_contribution == pytest.approx(
        0.1366666666666666
    )
    assert reconciliation.reconciliation_residual == pytest.approx(-0.016666666666666666)


def test_excludes_a_correction_published_after_prediction_time() -> None:
    contribution = _fx_adjusted_contribution()
    start_snapshot, original_end = _exact_prices()
    future_end = _fund_price(
        PERIOD_END,
        240.0,
        available_at=datetime(2026, 2, 1, 13, 0, tzinfo=UTC),
    )

    result = reconcile_point_in_time_fx_adjusted_fund_return(
        contribution,
        [start_snapshot, original_end, future_end],
        fund_price_source_id="tefas",
    )

    assert result.end_snapshot is original_end
    assert result.reconciliation_result.reconciliation.published_fund_return == pytest.approx(0.12)


def test_selects_the_latest_visible_correction() -> None:
    contribution = _fx_adjusted_contribution()
    start_snapshot, original_end = _exact_prices()
    corrected_end = _fund_price(
        PERIOD_END,
        230.0,
        available_at=datetime(2026, 2, 1, 11, 0, tzinfo=UTC),
    )

    result = reconcile_point_in_time_fx_adjusted_fund_return(
        contribution,
        [start_snapshot, original_end, corrected_end],
        fund_price_source_id="tefas",
    )

    assert result.end_snapshot is corrected_end
    reconciliation = result.reconciliation_result.reconciliation
    assert reconciliation.published_fund_return == pytest.approx(0.15)


def test_ignores_other_funds_and_sources() -> None:
    contribution = _fx_adjusted_contribution()
    start_snapshot, end_snapshot = _exact_prices()
    other_fund = _fund_price(PERIOD_END, 500.0, fund_id="OTHER")
    other_source = _fund_price(PERIOD_END, 600.0, source_id="other")

    result = reconcile_point_in_time_fx_adjusted_fund_return(
        contribution,
        [other_fund, other_source, end_snapshot, start_snapshot],
        fund_price_source_id="tefas",
    )

    assert result.start_snapshot is start_snapshot
    assert result.end_snapshot is end_snapshot


def test_rejects_a_missing_exact_start_snapshot() -> None:
    contribution = _fx_adjusted_contribution()
    end_snapshot = _fund_price(PERIOD_END, 224.0)

    with pytest.raises(MissingExactFundUnitPriceSnapshotError) as captured:
        reconcile_point_in_time_fx_adjusted_fund_return(
            contribution,
            [end_snapshot],
            fund_price_source_id="tefas",
        )

    assert captured.value.fund_id == "AAL"
    assert captured.value.source_id == "tefas"
    assert captured.value.required_date == PERIOD_START
    assert captured.value.prediction_timestamp == PREDICTION_TIMESTAMP


def test_rejects_a_missing_exact_end_snapshot() -> None:
    contribution = _fx_adjusted_contribution()
    start_snapshot = _fund_price(PERIOD_START, 200.0)

    with pytest.raises(MissingExactFundUnitPriceSnapshotError) as captured:
        reconcile_point_in_time_fx_adjusted_fund_return(
            contribution,
            [start_snapshot],
            fund_price_source_id="tefas",
        )

    assert captured.value.required_date == PERIOD_END


def test_does_not_substitute_a_nearby_snapshot() -> None:
    contribution = _fx_adjusted_contribution()
    nearby_start = _fund_price(MarketDate(2026, 1, 29), 198.0)
    end_snapshot = _fund_price(PERIOD_END, 224.0)

    with pytest.raises(MissingExactFundUnitPriceSnapshotError) as captured:
        reconcile_point_in_time_fx_adjusted_fund_return(
            contribution,
            [nearby_start, end_snapshot],
            fund_price_source_id="tefas",
        )

    assert captured.value.required_date == PERIOD_START


def test_consumes_a_one_shot_generator_once() -> None:
    contribution = _fx_adjusted_contribution()
    start_snapshot, end_snapshot = _exact_prices()

    def snapshots() -> Iterator[FundUnitPriceSnapshot]:
        yield end_snapshot
        yield start_snapshot

    result = reconcile_point_in_time_fx_adjusted_fund_return(
        contribution,
        snapshots(),
        fund_price_source_id="tefas",
    )

    assert result.start_snapshot is start_snapshot
    assert result.end_snapshot is end_snapshot


@pytest.mark.parametrize("source_id", ["", "   ", None, 42])
def test_rejects_an_invalid_fund_price_source(source_id: object) -> None:
    contribution = _fx_adjusted_contribution()

    with pytest.raises(InvalidFundPriceSourceError) as captured:
        reconcile_point_in_time_fx_adjusted_fund_return(
            contribution,
            _exact_prices(),
            fund_price_source_id=source_id,  # type: ignore[arg-type]
        )

    assert captured.value.source_id == source_id


def test_rejects_unexpected_native_return_cardinality() -> None:
    contribution = _fx_adjusted_contribution()
    start_snapshot, end_snapshot = _exact_prices()

    with patch(
        "navlens.reconciliation._snapshots.calculate_price_period_returns",
        return_value=[],
    ):
        with pytest.raises(UnexpectedNativeReturnCardinalityError) as captured:
            reconcile_point_in_time_fx_adjusted_fund_return(
                contribution,
                [start_snapshot, end_snapshot],
                fund_price_source_id="tefas",
            )

    assert captured.value.expected_count == 1
    assert captured.value.actual_count == 0


def test_delegates_both_financial_operations_to_native_bindings() -> None:
    contribution = _fx_adjusted_contribution()
    start_snapshot, end_snapshot = _exact_prices()
    native_period_return = object()
    native_reconciliation = object()

    with (
        patch(
            "navlens.reconciliation._snapshots.calculate_price_period_returns",
            return_value=[native_period_return],
        ) as calculate,
        patch(
            "navlens.reconciliation.fx_orchestration.reconcile_fx_adjusted_fund_return",
            return_value=native_reconciliation,
        ) as reconcile,
    ):
        result = reconcile_point_in_time_fx_adjusted_fund_return(
            contribution,
            [start_snapshot, end_snapshot],
            fund_price_source_id="tefas",
        )

    calculate.assert_called_once_with(
        "AAL",
        [start_snapshot.observation, end_snapshot.observation],
    )
    reconcile.assert_called_once_with(
        native_period_return,
        contribution.contribution_result,
    )
    assert result.reconciliation_result is native_reconciliation


def test_matches_legacy_orchestration_when_fx_return_is_zero() -> None:
    fx_contribution = _fx_adjusted_contribution(start_fx_rate=30.0, end_fx_rate=30.0)
    alignment = fx_contribution.request.alignment_result
    legacy_contribution = calculate_point_in_time_return_contribution(
        alignment,
        ReturnPeriod(PERIOD_START, PERIOD_END),
    )
    fund_prices = _exact_prices()

    fx_result = reconcile_point_in_time_fx_adjusted_fund_return(
        fx_contribution,
        fund_prices,
        fund_price_source_id="tefas",
    )
    legacy_result = reconcile_point_in_time_fund_return(
        legacy_contribution,
        fund_prices,
        fund_price_source_id="tefas",
    )

    assert fx_result.reconciliation_result == legacy_result.reconciliation_result
