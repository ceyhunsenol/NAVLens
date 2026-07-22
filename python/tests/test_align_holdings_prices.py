import pytest
from navlens import (
    AlignmentPolicy,
    AssetClass,
    CurrencyCode,
    HoldingPosition,
    MarketDate,
    NavlensValidationError,
    PriceAdjustment,
    SecurityPriceHistoryCandidate,
    SecurityPriceObservation,
    UnitPrice,
    align_holdings_prices,
)


def policy(*, minimum_observations: int = 2) -> AlignmentPolicy:
    return AlignmentPolicy(
        fund_base_currency=CurrencyCode("TRY"),
        required_price_adjustment=PriceAdjustment("total_return_adjusted"),
        pricing_as_of_date=MarketDate(2023, 10, 15),
        minimum_observations=minimum_observations,
        max_staleness_calendar_days=5,
    )


def holding(
    instrument_id: str,
    weight: float,
    asset_class: str = "equity",
) -> HoldingPosition:
    return HoldingPosition(instrument_id, AssetClass(asset_class), weight)


def observation(
    instrument_id: str,
    day: int,
    *,
    currency: str = "TRY",
    adjustment: str = "total_return_adjusted",
) -> SecurityPriceObservation:
    return SecurityPriceObservation(
        instrument_id,
        MarketDate(2023, 10, day),
        UnitPrice(10.0),
        CurrencyCode(currency),
        PriceAdjustment(adjustment),
    )


def candidate(
    instrument_id: str,
    days: list[int],
    *,
    currency: str = "TRY",
    adjustment: str = "total_return_adjusted",
) -> SecurityPriceHistoryCandidate:
    observations = [
        observation(
            instrument_id,
            day,
            currency=currency,
            adjustment=adjustment,
        )
        for day in days
    ]
    return SecurityPriceHistoryCandidate(instrument_id, observations)


def test_full_coverage_preserves_order_and_weights() -> None:
    holdings = [holding("INST_A", 0.3), holding("INST_B", 0.5, "exchange_traded_fund")]
    candidates = [candidate("INST_A", [14, 15]), candidate("INST_B", [13, 15])]

    report = align_holdings_prices(holdings, candidates, policy())

    assert [item.holding.instrument_id for item in report.covered] == ["INST_A", "INST_B"]
    assert report.uncovered_listed == []
    assert report.declared_weight == pytest.approx(0.8)
    assert report.covered_weight == pytest.approx(0.8)
    assert report.uncovered_listed_weight == pytest.approx(0.0)
    assert report.unrepresented_weight == pytest.approx(0.2)
    assert report.total_uncovered_weight == pytest.approx(0.2)
    assert report.coverage_ratio == pytest.approx(0.8)
    assert report.policy.minimum_observations == 2


def test_missing_price_series_is_reported_without_renormalization() -> None:
    report = align_holdings_prices([holding("INST_A", 0.5)], [], policy())

    assert report.covered == []
    assert report.uncovered_listed[0].holding.instrument_id == "INST_A"
    assert report.uncovered_listed[0].reason.kind == "missing_price_series"
    assert report.covered_weight == pytest.approx(0.0)
    assert report.total_uncovered_weight == pytest.approx(1.0)


def test_unsupported_asset_class_takes_precedence_over_candidate_contents() -> None:
    report = align_holdings_prices(
        [holding("DEBT", 0.5, "debt_security")],
        [candidate("DEBT", [16, 17], currency="USD", adjustment="unadjusted")],
        policy(),
    )

    reason = report.uncovered_listed[0].reason
    assert reason.kind == "unsupported_asset_class"
    assert reason.asset_class.name == "debt_security"


def test_insufficient_observations_exposes_counts() -> None:
    report = align_holdings_prices(
        [holding("INST_A", 0.5)],
        [candidate("INST_A", [15])],
        policy(),
    )

    reason = report.uncovered_listed[0].reason
    assert reason.kind == "insufficient_observations"
    assert reason.observations_found == 1
    assert reason.observations_required == 2


def test_currency_and_adjustment_gaps_preserve_payloads() -> None:
    holdings = [holding("CURRENCY", 0.5), holding("ADJUSTMENT", 0.5)]
    candidates = [
        candidate("CURRENCY", [14, 15], currency="USD"),
        candidate("ADJUSTMENT", [14, 15], adjustment="unadjusted"),
    ]

    report = align_holdings_prices(holdings, candidates, policy())
    currency_reason = report.uncovered_listed[0].reason
    adjustment_reason = report.uncovered_listed[1].reason

    assert currency_reason.kind == "currency_mismatch"
    assert currency_reason.expected_currency.code == "TRY"
    assert currency_reason.found_currency.code == "USD"
    assert adjustment_reason.kind == "incompatible_price_adjustment"
    assert adjustment_reason.expected_price_adjustment.name == "total_return_adjusted"
    assert adjustment_reason.found_price_adjustment.name == "unadjusted"


def test_stale_price_gap_preserves_policy_context() -> None:
    report = align_holdings_prices(
        [holding("STALE", 0.5)],
        [candidate("STALE", [8, 9])],
        policy(),
    )

    reason = report.uncovered_listed[0].reason
    assert reason.kind == "stale_prices"
    assert str(reason.latest_observation_date) == "2023-10-09"
    assert str(reason.pricing_as_of_date) == "2023-10-15"
    assert reason.max_staleness_calendar_days == 5


def test_duplicate_holding_is_a_typed_validation_error() -> None:
    holdings = [holding("DUPLICATE", 0.3), holding("DUPLICATE", 0.5)]

    with pytest.raises(NavlensValidationError, match="duplicate holding instrument"):
        align_holdings_prices(holdings, [], policy())


def test_future_observation_is_a_typed_validation_error() -> None:
    with pytest.raises(NavlensValidationError, match="is after pricing as-of date"):
        align_holdings_prices(
            [holding("FUTURE", 0.5)],
            [candidate("FUTURE", [16])],
            policy(),
        )


def test_binding_rejects_non_wrapper_inputs() -> None:
    with pytest.raises(TypeError):
        align_holdings_prices(["not-a-holding"], [], policy())
    with pytest.raises(TypeError):
        align_holdings_prices([], ["not-a-candidate"], policy())
    with pytest.raises(TypeError):
        align_holdings_prices([], [], "not-a-policy")
    with pytest.raises(TypeError):
        SecurityPriceHistoryCandidate("INST_A", ["not-an-observation"])


def test_policy_validation_delegates_to_rust_contract() -> None:
    with pytest.raises(NavlensValidationError, match="at least 2"):
        policy(minimum_observations=1)
