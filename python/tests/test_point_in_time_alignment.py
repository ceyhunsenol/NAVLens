from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from navlens import (
    AlignmentPolicy,
    AssetClass,
    CurrencyCode,
    HoldingPosition,
    HoldingSnapshot,
    MarketDate,
    MissingHoldingsSnapshotError,
    NavlensValidationError,
    PointInTimeAlignmentRequest,
    PriceAdjustment,
    SecurityPriceObservation,
    SecurityPriceSnapshot,
    UnitPrice,
    align_point_in_time,
)

PREDICTION_TIMESTAMP = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
PUBLICATION_TIMESTAMP = datetime(2026, 2, 1, 10, 0, tzinfo=UTC)


def policy() -> AlignmentPolicy:
    return AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("total_return_adjusted"),
        MarketDate(2026, 1, 31),
        2,
        5,
    )


def request(*, holdings_source_id: str = "kap") -> PointInTimeAlignmentRequest:
    return PointInTimeAlignmentRequest(
        "AAL",
        PREDICTION_TIMESTAMP,
        holdings_source_id,
        "market",
        policy(),
    )


def holdings_snapshot(
    positions: tuple[HoldingPosition, ...],
    *,
    source_id: str = "kap",
    published_at: datetime = PUBLICATION_TIMESTAMP,
) -> HoldingSnapshot:
    return HoldingSnapshot(
        fund_id="AAL",
        effective_date=MarketDate(2026, 1, 31),
        published_at=published_at,
        ingested_at=published_at,
        source_id=source_id,
        positions=positions,
    )


def price_snapshot(
    instrument_id: str,
    day: int,
    *,
    currency: str = "TRY",
    adjustment: str = "total_return_adjusted",
) -> SecurityPriceSnapshot:
    return SecurityPriceSnapshot(
        observation=SecurityPriceObservation(
            instrument_id,
            MarketDate(2026, 1, day),
            UnitPrice(10.0),
            CurrencyCode(currency),
            PriceAdjustment(adjustment),
        ),
        available_at=PUBLICATION_TIMESTAMP,
        ingested_at=PUBLICATION_TIMESTAMP,
        source_id="market",
    )


def equity(instrument_id: str, weight: float) -> HoldingPosition:
    return HoldingPosition(instrument_id, AssetClass("equity"), weight)


def test_selects_exact_holdings_source_and_reports_missing_context() -> None:
    selected = holdings_snapshot((equity("TARGET", 0.5),))
    other = holdings_snapshot((equity("OTHER", 0.5),), source_id="other")

    result = align_point_in_time(request(), [other, selected], [])

    assert result.holdings_snapshot == selected

    with pytest.raises(MissingHoldingsSnapshotError) as captured:
        align_point_in_time(request(holdings_source_id="missing"), [other, selected], [])
    assert captured.value.fund_id == "AAL"
    assert captured.value.source_id == "missing"
    assert captured.value.prediction_timestamp == PREDICTION_TIMESTAMP


def test_future_holdings_publication_is_invisible() -> None:
    future_timestamp = datetime(2026, 2, 1, 13, 0, tzinfo=UTC)
    future = holdings_snapshot((equity("FUTURE", 0.5),), published_at=future_timestamp)

    with pytest.raises(MissingHoldingsSnapshotError):
        align_point_in_time(request(), [future], [])


def test_materializes_generator_inputs_once() -> None:
    holdings = holdings_snapshot((equity("ONE", 0.5),))
    price = price_snapshot("ONE", 15)

    def holdings_generator() -> Iterator[HoldingSnapshot]:
        yield holdings

    def price_generator() -> Iterator[SecurityPriceSnapshot]:
        yield price

    result = align_point_in_time(request(), holdings_generator(), price_generator())

    assert result.holdings_snapshot == holdings
    assert result.selected_price_snapshots == (price,)


def test_preserves_rust_gaps_coverage_and_provenance_order() -> None:
    holdings = holdings_snapshot(
        (
            equity("MISSING", 0.1),
            equity("CURRENCY", 0.2),
            equity("ADJUSTMENT", 0.3),
            equity("COVERED", 0.4),
        )
    )
    currency_10 = price_snapshot("CURRENCY", 10, currency="USD")
    currency_11 = price_snapshot("CURRENCY", 11, currency="USD")
    adjustment_10 = price_snapshot("ADJUSTMENT", 10, adjustment="unadjusted")
    adjustment_11 = price_snapshot("ADJUSTMENT", 11, adjustment="unadjusted")
    covered_30 = price_snapshot("COVERED", 30)
    covered_31 = price_snapshot("COVERED", 31)
    shuffled_prices = [
        covered_31,
        currency_11,
        adjustment_10,
        covered_30,
        currency_10,
        adjustment_11,
    ]

    result = align_point_in_time(request(), [holdings], shuffled_prices)

    assert result.selected_price_snapshots == (
        currency_10,
        currency_11,
        adjustment_10,
        adjustment_11,
        covered_30,
        covered_31,
    )
    assert result.report.covered_weight == pytest.approx(0.4)
    assert result.report.declared_weight == pytest.approx(1.0)
    assert [item.holding.instrument_id for item in result.report.covered] == ["COVERED"]
    uncovered = {
        item.holding.instrument_id: item.reason.kind for item in result.report.uncovered_listed
    }
    assert uncovered == {
        "MISSING": "missing_price_series",
        "CURRENCY": "currency_mismatch",
        "ADJUSTMENT": "incompatible_price_adjustment",
    }


def test_mixed_series_remains_a_fatal_rust_error() -> None:
    holdings = holdings_snapshot((equity("MIXED", 0.5),))
    prices = [
        price_snapshot("MIXED", 10),
        price_snapshot("MIXED", 11, currency="USD"),
    ]

    with pytest.raises(NavlensValidationError, match="same currency"):
        align_point_in_time(request(), [holdings], prices)


def test_duplicate_holdings_remain_a_fatal_rust_error() -> None:
    holdings = holdings_snapshot((equity("DUPLICATE", 0.3), equity("DUPLICATE", 0.2)))

    with pytest.raises(NavlensValidationError, match="duplicate holding"):
        align_point_in_time(request(), [holdings], [])
