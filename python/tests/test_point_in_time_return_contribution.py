from datetime import UTC, datetime

import pytest
from navlens import (
    AlignmentPolicy,
    AssetClass,
    CurrencyCode,
    HoldingPosition,
    HoldingSnapshot,
    MarketDate,
    NavlensValidationError,
    PointInTimeAlignmentRequest,
    PriceAdjustment,
    ReturnPeriod,
    SecurityPriceObservation,
    SecurityPriceSnapshot,
    UnitPrice,
    align_point_in_time,
    calculate_point_in_time_return_contribution,
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


def request() -> PointInTimeAlignmentRequest:
    return PointInTimeAlignmentRequest(
        "AAL",
        PREDICTION_TIMESTAMP,
        "kap",
        "market",
        policy(),
    )


def holdings_snapshot(positions: tuple[HoldingPosition, ...]) -> HoldingSnapshot:
    return HoldingSnapshot(
        fund_id="AAL",
        effective_date=MarketDate(2026, 1, 31),
        published_at=PUBLICATION_TIMESTAMP,
        ingested_at=PUBLICATION_TIMESTAMP,
        source_id="kap",
        positions=positions,
    )


def price_snapshot(
    instrument_id: str,
    day: int,
    price: float = 10.0,
) -> SecurityPriceSnapshot:
    return SecurityPriceSnapshot(
        observation=SecurityPriceObservation(
            instrument_id,
            MarketDate(2026, 1, day),
            UnitPrice(price),
            CurrencyCode("TRY"),
            PriceAdjustment("total_return_adjusted"),
        ),
        available_at=PUBLICATION_TIMESTAMP,
        ingested_at=PUBLICATION_TIMESTAMP,
        source_id="market",
    )


def equity(instrument_id: str, weight: float) -> HoldingPosition:
    return HoldingPosition(instrument_id, AssetClass("equity"), weight)


def test_orchestration_produces_contribution_from_full_coverage() -> None:
    holdings = holdings_snapshot((equity("INST_A", 0.4), equity("INST_B", 0.6)))
    prices = [
        price_snapshot("INST_A", 30, 100.0),
        price_snapshot("INST_A", 31, 110.0),
        price_snapshot("INST_B", 30, 50.0),
        price_snapshot("INST_B", 31, 55.0),
    ]

    alignment_result = align_point_in_time(request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 30), MarketDate(2026, 1, 31))

    result = calculate_point_in_time_return_contribution(alignment_result, period)

    assert result.alignment_result is alignment_result
    assert len(result.contribution_result.component_contributions) == 2
    assert result.contribution_result.observed_contribution.has_full_coverage is True


def test_orchestration_preserves_object_identity_and_provenance() -> None:
    holdings = holdings_snapshot((equity("INST_A", 1.0),))
    prices = [
        price_snapshot("INST_A", 30, 100.0),
        price_snapshot("INST_A", 31, 110.0),
    ]

    alignment_result = align_point_in_time(request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 30), MarketDate(2026, 1, 31))

    result = calculate_point_in_time_return_contribution(alignment_result, period)

    assert result.alignment_result is alignment_result
    assert result.alignment_result.holdings_snapshot is alignment_result.holdings_snapshot
    assert (
        result.alignment_result.selected_price_snapshots
        == alignment_result.selected_price_snapshots
    )


def test_orchestration_preserves_partial_coverage_and_gaps() -> None:
    holdings = holdings_snapshot(
        (
            equity("PRICE_GAP", 0.2),
            equity("COVERED", 0.4),
            equity("RETURN_GAP", 0.4),
        )
    )
    prices = [
        price_snapshot("COVERED", 30, 100.0),
        price_snapshot("COVERED", 31, 110.0),
        price_snapshot("RETURN_GAP", 29, 100.0),
        price_snapshot("RETURN_GAP", 31, 110.0),
    ]

    alignment_result = align_point_in_time(request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 30), MarketDate(2026, 1, 31))

    result = calculate_point_in_time_return_contribution(alignment_result, period)

    contrib = result.contribution_result
    assert len(contrib.price_gaps) == 1
    assert contrib.price_gaps[0].holding.instrument_id == "PRICE_GAP"

    assert len(contrib.return_gaps) == 1
    assert contrib.return_gaps[0].holding.instrument_id == "RETURN_GAP"

    assert len(contrib.component_contributions) == 1
    assert contrib.component_contributions[0].holding.instrument_id == "COVERED"


def test_orchestration_transfers_negative_returns_correctly() -> None:
    holdings = holdings_snapshot((equity("NEGATIVE", 1.0),))
    prices = [
        price_snapshot("NEGATIVE", 30, 100.0),
        price_snapshot("NEGATIVE", 31, 50.0),
    ]

    alignment_result = align_point_in_time(request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 30), MarketDate(2026, 1, 31))

    result = calculate_point_in_time_return_contribution(alignment_result, period)

    comp = result.contribution_result.component_contributions[0]
    assert comp.contribution.weighted_contribution == pytest.approx(-0.5)


def test_orchestration_propagates_native_validation_errors() -> None:
    holdings = holdings_snapshot((equity("OVERFLOW", 1.0),))
    prices = [
        price_snapshot("OVERFLOW", 30, 1e-200),
        price_snapshot("OVERFLOW", 31, 1e300),
    ]

    alignment_result = align_point_in_time(request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 30), MarketDate(2026, 1, 31))

    with pytest.raises(NavlensValidationError):
        calculate_point_in_time_return_contribution(alignment_result, period)


def test_orchestration_does_not_consume_generators_again() -> None:
    holdings = holdings_snapshot((equity("INST_A", 1.0),))
    prices = [
        price_snapshot("INST_A", 30, 100.0),
        price_snapshot("INST_A", 31, 110.0),
    ]

    def holdings_gen():
        yield holdings

    def prices_gen():
        yield from prices

    alignment_result = align_point_in_time(request(), holdings_gen(), prices_gen())
    period = ReturnPeriod(MarketDate(2026, 1, 30), MarketDate(2026, 1, 31))

    result1 = calculate_point_in_time_return_contribution(alignment_result, period)
    result2 = calculate_point_in_time_return_contribution(alignment_result, period)

    assert result1.contribution_result.observed_contribution.observed_contribution == pytest.approx(
        0.1
    )
    assert result2.contribution_result.observed_contribution.observed_contribution == pytest.approx(
        0.1
    )
