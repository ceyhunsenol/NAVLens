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
    ReturnPeriod,
    SecurityPriceObservation,
    SecurityPriceSnapshot,
    UnitPrice,
    align_point_in_time,
    calculate_point_in_time_return_contribution,
    format_return_contribution_result,
)
from navlens.alignment.formatting import format_alignment_result

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


def test_full_coverage_formatting() -> None:
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

    formatted = format_return_contribution_result(result)
    expected_alignment = format_alignment_result(alignment_result)

    expected = f"""{expected_alignment}

Return Contribution Report
==========================
Target Period: 2026-01-30 to 2026-01-31
Price Coverage: 1.000000
Return Coverage: 1.000000
Observed Contribution: 0.100000
Has Full Coverage: True

Component Contributions:
  - INST_A (weight: 0.400000, market return: 0.100000, weighted contribution: 0.040000)
  - INST_B (weight: 0.600000, market return: 0.100000, weighted contribution: 0.060000)

Price Gaps:
  (none)

Return Gaps:
  (none)"""

    assert formatted == expected


def test_partial_coverage_shows_all_sections_in_order() -> None:
    holdings = holdings_snapshot(
        (
            equity("PRICE_GAP_1", 0.1),
            equity("PRICE_GAP_2", 0.1),
            equity("COVERED_1", 0.2),
            equity("COVERED_2", 0.2),
            equity("RETURN_GAP_1", 0.2),
            equity("RETURN_GAP_2", 0.2),
        )
    )
    prices = [
        price_snapshot("COVERED_1", 30, 100.0),
        price_snapshot("COVERED_1", 31, 110.0),
        price_snapshot("COVERED_2", 30, 100.0),
        price_snapshot("COVERED_2", 31, 110.0),
        price_snapshot("RETURN_GAP_1", 29, 100.0),
        price_snapshot("RETURN_GAP_1", 31, 110.0),
        price_snapshot("RETURN_GAP_2", 29, 100.0),
        price_snapshot("RETURN_GAP_2", 31, 110.0),
    ]

    alignment_result = align_point_in_time(request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 30), MarketDate(2026, 1, 31))
    result = calculate_point_in_time_return_contribution(alignment_result, period)

    formatted = format_return_contribution_result(result)

    comp_idx = formatted.index("Component Contributions:")
    comp_1_idx = formatted.index("  - COVERED_1", comp_idx)
    comp_2_idx = formatted.index("  - COVERED_2", comp_1_idx)

    price_gap_idx = formatted.index("Price Gaps:", comp_2_idx)
    price_gap_1_idx = formatted.index("  - PRICE_GAP_1", price_gap_idx)
    price_gap_2_idx = formatted.index("  - PRICE_GAP_2", price_gap_1_idx)

    return_gap_idx = formatted.index("Return Gaps:", price_gap_2_idx)
    return_gap_1_idx = formatted.index("  - RETURN_GAP_1", return_gap_idx)
    return_gap_2_idx = formatted.index("  - RETURN_GAP_2", return_gap_1_idx)

    assert (
        comp_idx
        < comp_1_idx
        < comp_2_idx
        < price_gap_idx
        < price_gap_1_idx
        < price_gap_2_idx
        < return_gap_idx
        < return_gap_1_idx
        < return_gap_2_idx
    )


def test_negative_return_is_formatted_correctly() -> None:
    holdings = holdings_snapshot((equity("NEGATIVE", 1.0),))
    prices = [
        price_snapshot("NEGATIVE", 30, 100.0),
        price_snapshot("NEGATIVE", 31, 50.0),
    ]

    alignment_result = align_point_in_time(request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 30), MarketDate(2026, 1, 31))
    result = calculate_point_in_time_return_contribution(alignment_result, period)

    formatted = format_return_contribution_result(result)

    assert "market return: -0.500000" in formatted
    assert "weighted contribution: -0.500000" in formatted
    assert "Observed Contribution: -0.500000" in formatted


def test_empty_lists_show_none() -> None:
    holdings = holdings_snapshot((equity("PRICE_GAP", 1.0),))
    prices = []

    alignment_result = align_point_in_time(request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 30), MarketDate(2026, 1, 31))
    result = calculate_point_in_time_return_contribution(alignment_result, period)

    formatted = format_return_contribution_result(result)

    assert "Component Contributions:\n  (none)" in formatted
    assert "Return Gaps:\n  (none)" in formatted
    assert "Price Gaps:\n  - PRICE_GAP" in formatted


def test_formatting_is_deterministic_and_pure() -> None:
    holdings = holdings_snapshot((equity("INST_A", 1.0),))
    prices = [
        price_snapshot("INST_A", 30, 100.0),
        price_snapshot("INST_A", 31, 110.0),
    ]

    alignment_result = align_point_in_time(request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 30), MarketDate(2026, 1, 31))
    result = calculate_point_in_time_return_contribution(alignment_result, period)

    formatted1 = format_return_contribution_result(result)
    formatted2 = format_return_contribution_result(result)

    assert formatted1 == formatted2


def test_preserves_alignment_provenance_header() -> None:
    holdings = holdings_snapshot((equity("INST_A", 1.0),))
    prices = [
        price_snapshot("INST_A", 30, 100.0),
        price_snapshot("INST_A", 31, 110.0),
    ]

    alignment_result = align_point_in_time(request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 30), MarketDate(2026, 1, 31))
    result = calculate_point_in_time_return_contribution(alignment_result, period)

    formatted = format_return_contribution_result(result)
    expected_header = format_alignment_result(alignment_result)

    assert formatted.startswith(expected_header)
