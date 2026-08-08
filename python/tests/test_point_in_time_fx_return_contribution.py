from datetime import UTC, datetime

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
    InvalidPointInTimeFxReturnContributionRequestError,
    MarketDate,
    NavlensValidationError,
    PointInTimeAlignmentRequest,
    PointInTimeFxAdjustedReturnContributionResult,
    PointInTimeFxReturnContributionRequest,
    PriceAdjustment,
    PriceCurrencyPolicy,
    ReturnPeriod,
    SecurityPriceObservation,
    SecurityPriceSnapshot,
    UnitPrice,
    align_point_in_time,
    calculate_point_in_time_fx_adjusted_return_contribution,
)
from navlens.datasets import FxRateSnapshot

PREDICTION_TIMESTAMP = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)
PUBLICATION_TIMESTAMP = datetime(2026, 2, 1, 10, 0, tzinfo=UTC)


def permit_foreign_policy() -> AlignmentPolicy:
    return AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("unadjusted"),
        MarketDate(2026, 1, 31),
        2,
        0,
    ).with_price_currency_policy(PriceCurrencyPolicy("permit_foreign"))


def fund_base_only_policy() -> AlignmentPolicy:
    return AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("unadjusted"),
        MarketDate(2026, 1, 31),
        2,
        0,
    )


def alignment_request(pol: AlignmentPolicy | None = None) -> PointInTimeAlignmentRequest:
    return PointInTimeAlignmentRequest(
        "AAL",
        PREDICTION_TIMESTAMP,
        "kap",
        "market",
        pol or permit_foreign_policy(),
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
    price: float,
    currency: str = "TRY",
) -> SecurityPriceSnapshot:
    return SecurityPriceSnapshot(
        observation=SecurityPriceObservation(
            instrument_id,
            MarketDate(2026, 1, day),
            UnitPrice(price),
            CurrencyCode(currency),
            PriceAdjustment("unadjusted"),
        ),
        available_at=PUBLICATION_TIMESTAMP,
        ingested_at=PUBLICATION_TIMESTAMP,
        source_id="market",
    )


def fx_snapshot(
    base: str,
    quote: str,
    day: int,
    rate: float,
    kind: str = "non_cash_buying",
    source_id: str = "tcmb",
    available_at: datetime = PUBLICATION_TIMESTAMP,
) -> FxRateSnapshot:
    return FxRateSnapshot(
        observation=FxRateObservation(
            CurrencyPair(CurrencyCode(base), CurrencyCode(quote)),
            MarketDate(2026, 1, day),
            FxRate(rate),
            FxRateKind(kind),
        ),
        available_at=available_at,
        ingested_at=available_at,
        source_id=source_id,
    )


def equity(instrument_id: str, weight: float) -> HoldingPosition:
    return HoldingPosition(instrument_id, AssetClass("equity"), weight)


def test_same_currency_portfolios_require_no_fx_snapshots() -> None:
    holdings = holdings_snapshot((equity("INST_TRY", 1.0),))
    prices = [
        price_snapshot("INST_TRY", 1, 100.0, "TRY"),
        price_snapshot("INST_TRY", 31, 110.0, "TRY"),
    ]
    align_res = align_point_in_time(alignment_request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 31))

    req = PointInTimeFxReturnContributionRequest(
        alignment_result=align_res,
        target_period=period,
        fx_source_id="tcmb",
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
    )

    res = calculate_point_in_time_fx_adjusted_return_contribution(req, [])

    assert res.request is req
    assert len(res.contribution_result.component_contributions) == 1
    comp = res.contribution_result.component_contributions[0]
    assert comp.currency_adjustment.is_not_required
    assert abs(comp.effective_base_currency_return - 0.1) < 1e-9
    assert res.selected_fx_snapshots == ()


def test_successful_usd_try_adjustment() -> None:
    holdings = holdings_snapshot((equity("INST_USD", 1.0),))
    prices = [
        price_snapshot("INST_USD", 1, 100.0, "USD"),
        price_snapshot("INST_USD", 31, 110.0, "USD"),
    ]
    align_res = align_point_in_time(alignment_request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 31))

    fx_snaps = [
        fx_snapshot("USD", "TRY", 1, 30.0),
        fx_snapshot("USD", "TRY", 31, 33.0),
    ]

    req = PointInTimeFxReturnContributionRequest(
        alignment_result=align_res,
        target_period=period,
        fx_source_id="tcmb",
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
    )

    res = calculate_point_in_time_fx_adjusted_return_contribution(req, fx_snaps)

    assert isinstance(res, PointInTimeFxAdjustedReturnContributionResult)
    assert len(res.contribution_result.component_contributions) == 1
    comp = res.contribution_result.component_contributions[0]
    assert comp.currency_adjustment.is_applied
    # Security return (10%) * FX return (10%) => 21%
    assert abs(comp.effective_base_currency_return - 0.21) < 1e-9
    assert len(res.selected_fx_snapshots) == 2
    assert res.selected_fx_snapshots[0] is fx_snaps[0]
    assert res.selected_fx_snapshots[1] is fx_snaps[1]


def test_multiple_holdings_sharing_one_pair_create_one_candidate_series() -> None:
    holdings = holdings_snapshot((equity("INST_USD_1", 0.5), equity("INST_USD_2", 0.5)))
    prices = [
        price_snapshot("INST_USD_1", 1, 100.0, "USD"),
        price_snapshot("INST_USD_1", 31, 110.0, "USD"),
        price_snapshot("INST_USD_2", 1, 50.0, "USD"),
        price_snapshot("INST_USD_2", 31, 55.0, "USD"),
    ]
    align_res = align_point_in_time(alignment_request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 31))

    fx_snaps = [
        fx_snapshot("USD", "TRY", 1, 30.0),
        fx_snapshot("USD", "TRY", 31, 33.0),
    ]

    req = PointInTimeFxReturnContributionRequest(
        alignment_result=align_res,
        target_period=period,
        fx_source_id="tcmb",
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
    )

    res = calculate_point_in_time_fx_adjusted_return_contribution(req, fx_snaps)

    assert len(res.contribution_result.component_contributions) == 2
    assert len(res.selected_fx_snapshots) == 2


def test_multiple_distinct_required_pairs() -> None:
    holdings = holdings_snapshot((equity("INST_USD", 0.5), equity("INST_EUR", 0.5)))
    prices = [
        price_snapshot("INST_USD", 1, 100.0, "USD"),
        price_snapshot("INST_USD", 31, 110.0, "USD"),
        price_snapshot("INST_EUR", 1, 100.0, "EUR"),
        price_snapshot("INST_EUR", 31, 105.0, "EUR"),
    ]
    align_res = align_point_in_time(alignment_request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 31))

    fx_snaps = [
        fx_snapshot("USD", "TRY", 1, 30.0),
        fx_snapshot("USD", "TRY", 31, 33.0),
        fx_snapshot("EUR", "TRY", 1, 32.0),
        fx_snapshot("EUR", "TRY", 31, 35.2),
    ]

    req = PointInTimeFxReturnContributionRequest(
        alignment_result=align_res,
        target_period=period,
        fx_source_id="tcmb",
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
    )

    res = calculate_point_in_time_fx_adjusted_return_contribution(req, fx_snaps)

    assert len(res.contribution_result.component_contributions) == 2
    assert res.contribution_result.observed_contribution.has_full_coverage is True
    assert len(res.selected_fx_snapshots) == 4


def test_future_published_fx_corrections_are_excluded() -> None:
    holdings = holdings_snapshot((equity("INST_USD", 1.0),))
    prices = [
        price_snapshot("INST_USD", 1, 100.0, "USD"),
        price_snapshot("INST_USD", 31, 110.0, "USD"),
    ]
    align_res = align_point_in_time(alignment_request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 31))

    future_published = datetime(2026, 2, 2, 12, 0, tzinfo=UTC)

    fx_snaps = [
        fx_snapshot("USD", "TRY", 1, 30.0),
        fx_snapshot("USD", "TRY", 31, 33.0),
        # Published in future after prediction timestamp
        fx_snapshot("USD", "TRY", 31, 35.0, available_at=future_published),
    ]

    req = PointInTimeFxReturnContributionRequest(
        alignment_result=align_res,
        target_period=period,
        fx_source_id="tcmb",
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
    )

    res = calculate_point_in_time_fx_adjusted_return_contribution(req, fx_snaps)

    assert len(res.selected_fx_snapshots) == 2
    assert all(snap.available_at <= PREDICTION_TIMESTAMP for snap in res.selected_fx_snapshots)


def test_exact_provider_pair_and_kind_isolation() -> None:
    holdings = holdings_snapshot((equity("INST_USD", 1.0),))
    prices = [
        price_snapshot("INST_USD", 1, 100.0, "USD"),
        price_snapshot("INST_USD", 31, 110.0, "USD"),
    ]
    align_res = align_point_in_time(alignment_request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 31))

    valid_snap_1 = fx_snapshot("USD", "TRY", 1, 30.0, kind="non_cash_buying", source_id="tcmb")
    valid_snap_2 = fx_snapshot("USD", "TRY", 31, 33.0, kind="non_cash_buying", source_id="tcmb")

    fx_snaps = [
        valid_snap_1,
        valid_snap_2,
        # Wrong source
        fx_snapshot("USD", "TRY", 1, 29.0, kind="non_cash_buying", source_id="other"),
        # Wrong kind
        fx_snapshot("USD", "TRY", 1, 30.5, kind="cash_selling", source_id="tcmb"),
        # Unrelated pair
        fx_snapshot("GBP", "TRY", 1, 40.0, kind="non_cash_buying", source_id="tcmb"),
    ]

    req = PointInTimeFxReturnContributionRequest(
        alignment_result=align_res,
        target_period=period,
        fx_source_id="tcmb",
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
    )

    res = calculate_point_in_time_fx_adjusted_return_contribution(req, fx_snaps)

    assert res.selected_fx_snapshots == (valid_snap_1, valid_snap_2)


def test_missing_pair_remains_typed_native_coverage_gap() -> None:
    holdings = holdings_snapshot((equity("INST_USD", 1.0),))
    prices = [
        price_snapshot("INST_USD", 1, 100.0, "USD"),
        price_snapshot("INST_USD", 31, 110.0, "USD"),
    ]
    align_res = align_point_in_time(alignment_request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 31))

    req = PointInTimeFxReturnContributionRequest(
        alignment_result=align_res,
        target_period=period,
        fx_source_id="tcmb",
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
    )

    res = calculate_point_in_time_fx_adjusted_return_contribution(req, [])

    assert len(res.contribution_result.return_gaps) == 1
    reason = res.contribution_result.return_gaps[0].reason
    assert reason.kind == "missing_direct_fx_candidate"
    assert reason.required_pair == CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))


def test_partial_fx_coverage_preserved_without_renormalization() -> None:
    holdings = holdings_snapshot((equity("INST_USD", 0.5), equity("INST_EUR", 0.5)))
    prices = [
        price_snapshot("INST_USD", 1, 100.0, "USD"),
        price_snapshot("INST_USD", 31, 110.0, "USD"),
        price_snapshot("INST_EUR", 1, 100.0, "EUR"),
        price_snapshot("INST_EUR", 31, 110.0, "EUR"),
    ]
    align_res = align_point_in_time(alignment_request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 31))

    # Only USD/TRY is provided
    fx_snaps = [
        fx_snapshot("USD", "TRY", 1, 30.0),
        fx_snapshot("USD", "TRY", 31, 33.0),
    ]

    req = PointInTimeFxReturnContributionRequest(
        alignment_result=align_res,
        target_period=period,
        fx_source_id="tcmb",
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
    )

    res = calculate_point_in_time_fx_adjusted_return_contribution(req, fx_snaps)

    assert len(res.contribution_result.component_contributions) == 1
    assert len(res.contribution_result.return_gaps) == 1
    assert res.contribution_result.observed_contribution.return_coverage == 0.5
    # Contribution from USD = 0.5 * 0.21 = 0.105
    assert abs(res.contribution_result.observed_contribution.observed_contribution - 0.105) < 1e-9


def test_deterministic_provenance_ordering_under_shuffled_input() -> None:
    holdings_eur_first = holdings_snapshot((equity("INST_EUR", 0.5), equity("INST_USD", 0.5)))
    holdings_usd_first = holdings_snapshot((equity("INST_USD", 0.5), equity("INST_EUR", 0.5)))
    prices = [
        price_snapshot("INST_USD", 1, 100.0, "USD"),
        price_snapshot("INST_USD", 31, 110.0, "USD"),
        price_snapshot("INST_EUR", 1, 100.0, "EUR"),
        price_snapshot("INST_EUR", 31, 110.0, "EUR"),
    ]
    align_res_eur_first = align_point_in_time(alignment_request(), [holdings_eur_first], prices)
    align_res_usd_first = align_point_in_time(alignment_request(), [holdings_usd_first], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 31))

    fx_1 = fx_snapshot("EUR", "TRY", 1, 32.0)
    fx_2 = fx_snapshot("EUR", "TRY", 31, 35.2)
    fx_3 = fx_snapshot("USD", "TRY", 1, 30.0)
    fx_4 = fx_snapshot("USD", "TRY", 31, 33.0)

    fx_snaps = [fx_4, fx_1, fx_3, fx_2]

    req_eur_first = PointInTimeFxReturnContributionRequest(
        alignment_result=align_res_eur_first,
        target_period=period,
        fx_source_id="tcmb",
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
    )
    req_usd_first = PointInTimeFxReturnContributionRequest(
        alignment_result=align_res_usd_first,
        target_period=period,
        fx_source_id="tcmb",
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
    )

    res1 = calculate_point_in_time_fx_adjusted_return_contribution(req_eur_first, fx_snaps)
    res2 = calculate_point_in_time_fx_adjusted_return_contribution(
        req_usd_first, list(reversed(fx_snaps))
    )

    # Order must be EUR (day 1, day 31) then USD (day 1, day 31)
    expected_order = (fx_1, fx_2, fx_3, fx_4)
    assert res1.selected_fx_snapshots == expected_order
    assert res2.selected_fx_snapshots == expected_order


def test_generator_inputs_consumed_once() -> None:
    holdings = holdings_snapshot((equity("INST_USD", 1.0),))
    prices = [
        price_snapshot("INST_USD", 1, 100.0, "USD"),
        price_snapshot("INST_USD", 31, 110.0, "USD"),
    ]
    align_res = align_point_in_time(alignment_request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 31))

    fx_snaps = [
        fx_snapshot("USD", "TRY", 1, 30.0),
        fx_snapshot("USD", "TRY", 31, 33.0),
    ]

    req = PointInTimeFxReturnContributionRequest(
        alignment_result=align_res,
        target_period=period,
        fx_source_id="tcmb",
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
    )

    class SinglePassSnapshots:
        def __init__(self, snapshots: list[FxRateSnapshot]) -> None:
            self.snapshots = snapshots
            self.iteration_count = 0

        def __iter__(self):
            self.iteration_count += 1
            if self.iteration_count > 1:
                raise AssertionError("FX snapshots iterable was consumed more than once")
            return iter(self.snapshots)

    single_pass_snapshots = SinglePassSnapshots(fx_snaps)
    res = calculate_point_in_time_fx_adjusted_return_contribution(req, single_pass_snapshots)

    assert len(res.selected_fx_snapshots) == 2
    assert single_pass_snapshots.iteration_count == 1


def test_reverse_pairs_are_not_accepted() -> None:
    holdings = holdings_snapshot((equity("INST_USD", 1.0),))
    prices = [
        price_snapshot("INST_USD", 1, 100.0, "USD"),
        price_snapshot("INST_USD", 31, 110.0, "USD"),
    ]
    align_res = align_point_in_time(alignment_request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 31))

    # Reverse pair TRY/USD instead of USD/TRY
    reverse_snaps = [
        fx_snapshot("TRY", "USD", 1, 1.0 / 30.0),
        fx_snapshot("TRY", "USD", 31, 1.0 / 33.0),
    ]

    req = PointInTimeFxReturnContributionRequest(
        alignment_result=align_res,
        target_period=period,
        fx_source_id="tcmb",
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
    )

    res = calculate_point_in_time_fx_adjusted_return_contribution(req, reverse_snaps)

    assert len(res.selected_fx_snapshots) == 0
    assert len(res.contribution_result.return_gaps) == 1
    assert res.contribution_result.return_gaps[0].reason.kind == "missing_direct_fx_candidate"


def test_native_validation_errors_propagate_unchanged() -> None:
    holdings = holdings_snapshot((equity("OVERFLOW", 1.0),))
    prices = [
        price_snapshot("OVERFLOW", 1, 1e-200, "TRY"),
        price_snapshot("OVERFLOW", 31, 1e300, "TRY"),
    ]
    align_res = align_point_in_time(alignment_request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 31))

    req = PointInTimeFxReturnContributionRequest(
        alignment_result=align_res,
        target_period=period,
        fx_source_id="tcmb",
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
    )

    with pytest.raises(NavlensValidationError):
        calculate_point_in_time_fx_adjusted_return_contribution(req, [])


def test_request_contract_immutability_and_validation() -> None:
    holdings = holdings_snapshot((equity("INST_USD", 1.0),))
    prices = [
        price_snapshot("INST_USD", 1, 100.0, "USD"),
        price_snapshot("INST_USD", 31, 110.0, "USD"),
    ]
    align_res = align_point_in_time(alignment_request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 31))
    policy = FxReturnPolicy(FxRateKind("non_cash_buying"), 0)

    req = PointInTimeFxReturnContributionRequest(
        alignment_result=align_res,
        target_period=period,
        fx_source_id="tcmb",
        fx_policy=policy,
    )

    with pytest.raises(AttributeError):
        req.fx_source_id = "other"  # type: ignore[misc]

    # Test invalid field types
    with pytest.raises(InvalidPointInTimeFxReturnContributionRequestError):
        PointInTimeFxReturnContributionRequest(
            alignment_result="invalid",  # type: ignore[arg-type]
            target_period=period,
            fx_source_id="tcmb",
            fx_policy=policy,
        )

    with pytest.raises(InvalidPointInTimeFxReturnContributionRequestError):
        PointInTimeFxReturnContributionRequest(
            alignment_result=align_res,
            target_period="invalid",  # type: ignore[arg-type]
            fx_source_id="tcmb",
            fx_policy=policy,
        )

    with pytest.raises(InvalidPointInTimeFxReturnContributionRequestError):
        PointInTimeFxReturnContributionRequest(
            alignment_result=align_res,
            target_period=period,
            fx_source_id="   ",  # whitespace
            fx_policy=policy,
        )

    with pytest.raises(InvalidPointInTimeFxReturnContributionRequestError):
        PointInTimeFxReturnContributionRequest(
            alignment_result=align_res,
            target_period=period,
            fx_source_id="tcmb",
            fx_policy="invalid",  # type: ignore[arg-type]
        )


def test_incompatible_alignment_policy_rejection() -> None:
    holdings = holdings_snapshot((equity("INST_USD", 1.0),))
    prices = [
        price_snapshot("INST_USD", 1, 100.0, "USD"),
        price_snapshot("INST_USD", 31, 110.0, "USD"),
    ]
    # Use default policy (fund_base_only)
    align_res = align_point_in_time(alignment_request(fund_base_only_policy()), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 31))

    with pytest.raises(InvalidPointInTimeFxReturnContributionRequestError, match="permit foreign"):
        PointInTimeFxReturnContributionRequest(
            alignment_result=align_res,
            target_period=period,
            fx_source_id="tcmb",
            fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
        )


def test_selected_snapshot_object_identity_preserved() -> None:
    holdings = holdings_snapshot((equity("INST_USD", 1.0),))
    prices = [
        price_snapshot("INST_USD", 1, 100.0, "USD"),
        price_snapshot("INST_USD", 31, 110.0, "USD"),
    ]
    align_res = align_point_in_time(alignment_request(), [holdings], prices)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 31))

    snap1 = fx_snapshot("USD", "TRY", 1, 30.0)
    snap2 = fx_snapshot("USD", "TRY", 31, 33.0)

    req = PointInTimeFxReturnContributionRequest(
        alignment_result=align_res,
        target_period=period,
        fx_source_id="tcmb",
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
    )

    res = calculate_point_in_time_fx_adjusted_return_contribution(req, [snap1, snap2])

    assert res.selected_fx_snapshots[0] is snap1
    assert res.selected_fx_snapshots[1] is snap2
