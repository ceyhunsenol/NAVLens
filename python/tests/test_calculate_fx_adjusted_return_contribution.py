import pytest
from navlens import (
    AlignmentPolicy,
    AssetClass,
    CurrencyCode,
    CurrencyPair,
    FxRate,
    FxRateKind,
    FxRateObservation,
    FxRateSeries,
    FxReturnPolicy,
    HoldingPosition,
    MarketDate,
    NavlensValidationError,
    PriceAdjustment,
    PriceCurrencyPolicy,
    ReturnPeriod,
    SecurityPriceHistoryCandidate,
    SecurityPriceObservation,
    UnitPrice,
    align_holdings_prices,
    calculate_fx_adjusted_return_contribution,
)


def test_price_currency_policy_canonical_values():
    assert PriceCurrencyPolicy("fund_base_only").name == "fund_base_only"
    assert PriceCurrencyPolicy("permit_foreign").name == "permit_foreign"
    assert hash(PriceCurrencyPolicy("permit_foreign")) == hash(
        PriceCurrencyPolicy("permit_foreign")
    )

    with pytest.raises(NavlensValidationError):
        PriceCurrencyPolicy("invalid")


def test_alignment_policy_default_remains_fund_base_only():
    policy = AlignmentPolicy(
        fund_base_currency=CurrencyCode("TRY"),
        required_price_adjustment=PriceAdjustment("unadjusted"),
        pricing_as_of_date=MarketDate(2025, 1, 31),
        minimum_observations=2,
        max_staleness_calendar_days=0,
    )
    assert policy.price_currency_policy == PriceCurrencyPolicy("fund_base_only")


def test_immutable_permit_foreign_configuration():
    base_policy = AlignmentPolicy(
        fund_base_currency=CurrencyCode("TRY"),
        required_price_adjustment=PriceAdjustment("unadjusted"),
        pricing_as_of_date=MarketDate(2025, 1, 31),
        minimum_observations=2,
        max_staleness_calendar_days=0,
    )
    new_policy = base_policy.with_price_currency_policy(PriceCurrencyPolicy("permit_foreign"))

    assert base_policy.price_currency_policy == PriceCurrencyPolicy("fund_base_only")
    assert new_policy.price_currency_policy == PriceCurrencyPolicy("permit_foreign")


def test_fx_return_policy_getter_parity():
    policy = FxReturnPolicy(FxRateKind("non_cash_buying"), 3)
    assert policy.required_fx_rate_kind == FxRateKind("non_cash_buying")
    assert policy.max_fx_staleness_calendar_days == 3


@pytest.fixture
def base_report():
    holdings = [HoldingPosition("INST-1", AssetClass("equity"), 1.0)]
    candidates = [
        SecurityPriceHistoryCandidate(
            "INST-1",
            [
                SecurityPriceObservation(
                    "INST-1",
                    MarketDate(2025, 1, 1),
                    UnitPrice(100.0),
                    CurrencyCode("USD"),
                    PriceAdjustment("unadjusted"),
                ),
                SecurityPriceObservation(
                    "INST-1",
                    MarketDate(2025, 1, 31),
                    UnitPrice(110.0),
                    CurrencyCode("USD"),
                    PriceAdjustment("unadjusted"),
                ),
            ],
        )
    ]
    policy = AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("unadjusted"),
        MarketDate(2025, 1, 31),
        2,
        0,
    ).with_price_currency_policy(PriceCurrencyPolicy("permit_foreign"))

    return align_holdings_prices(holdings, candidates, policy)


def create_fx(dates_and_rates, kind="non_cash_buying"):
    return FxRateSeries(
        [
            FxRateObservation(
                CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY")),
                MarketDate(2025, 1, d),
                FxRate(r),
                FxRateKind(kind),
            )
            for d, r in dates_and_rates
        ]
    )


def test_same_currency_calculation_with_not_required_adjustment():
    holdings = [HoldingPosition("INST-1", AssetClass("equity"), 1.0)]
    candidates = [
        SecurityPriceHistoryCandidate(
            "INST-1",
            [
                SecurityPriceObservation(
                    "INST-1",
                    MarketDate(2025, 1, 1),
                    UnitPrice(100.0),
                    CurrencyCode("TRY"),
                    PriceAdjustment("unadjusted"),
                ),
                SecurityPriceObservation(
                    "INST-1",
                    MarketDate(2025, 1, 31),
                    UnitPrice(110.0),
                    CurrencyCode("TRY"),
                    PriceAdjustment("unadjusted"),
                ),
            ],
        )
    ]
    policy = AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("unadjusted"),
        MarketDate(2025, 1, 31),
        2,
        0,
    ).with_price_currency_policy(PriceCurrencyPolicy("permit_foreign"))

    report = align_holdings_prices(holdings, candidates, policy)
    period = ReturnPeriod(MarketDate(2025, 1, 1), MarketDate(2025, 1, 31))

    result = calculate_fx_adjusted_return_contribution(
        report, period, [], FxReturnPolicy(FxRateKind("non_cash_buying"), 0)
    )

    assert len(result.component_contributions) == 1
    comp = result.component_contributions[0]
    assert comp.currency_adjustment.is_not_required
    assert not comp.currency_adjustment.is_applied
    assert comp.currency_adjustment.applied_evidence is None
    assert abs(comp.effective_base_currency_return - 0.1) < 1e-9


def test_foreign_currency_multiplicative_fx_result_parity_with_rust(base_report):
    fx = [create_fx([(1, 30.0), (31, 33.0)])]
    period = ReturnPeriod(MarketDate(2025, 1, 1), MarketDate(2025, 1, 31))

    result = calculate_fx_adjusted_return_contribution(
        base_report, period, fx, FxReturnPolicy(FxRateKind("non_cash_buying"), 0)
    )

    assert len(result.component_contributions) == 1
    comp = result.component_contributions[0]
    assert comp.currency_adjustment.is_applied

    ev = comp.currency_adjustment.applied_evidence
    assert ev is not None
    assert ev.required_pair == CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    assert ev.required_kind == FxRateKind("non_cash_buying")

    # Security return = (110 / 100) - 1 = 0.1
    # FX return = (33 / 30) - 1 = 0.1
    # Total return = (1.1 * 1.1) - 1 = 0.21
    assert abs(comp.effective_base_currency_return - 0.21) < 1e-9


def test_requested_actual_fx_evidence_dates_and_staleness(base_report):
    fx = [create_fx([(1, 30.0), (30, 33.0)])]
    period = ReturnPeriod(MarketDate(2025, 1, 5), MarketDate(2025, 1, 31))

    holdings = [HoldingPosition("INST-1", AssetClass("equity"), 1.0)]
    candidates = [
        SecurityPriceHistoryCandidate(
            "INST-1",
            [
                SecurityPriceObservation(
                    "INST-1",
                    MarketDate(2025, 1, 5),
                    UnitPrice(100.0),
                    CurrencyCode("USD"),
                    PriceAdjustment("unadjusted"),
                ),
                SecurityPriceObservation(
                    "INST-1",
                    MarketDate(2025, 1, 31),
                    UnitPrice(110.0),
                    CurrencyCode("USD"),
                    PriceAdjustment("unadjusted"),
                ),
            ],
        )
    ]
    policy = AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("unadjusted"),
        MarketDate(2025, 1, 31),
        2,
        0,
    ).with_price_currency_policy(PriceCurrencyPolicy("permit_foreign"))
    report = align_holdings_prices(holdings, candidates, policy)

    result = calculate_fx_adjusted_return_contribution(
        report, period, fx, FxReturnPolicy(FxRateKind("non_cash_buying"), 4)
    )

    comp = result.component_contributions[0]
    ev = comp.currency_adjustment.applied_evidence

    assert ev.start.requested_date == MarketDate(2025, 1, 5)
    assert ev.start.observation.market_date == MarketDate(2025, 1, 1)
    assert ev.start.staleness_calendar_days == 4

    assert ev.end.requested_date == MarketDate(2025, 1, 31)
    assert ev.end.observation.market_date == MarketDate(2025, 1, 30)
    assert ev.end.staleness_calendar_days == 1


def test_typed_component_contribution_and_effective_return(base_report):
    fx = [create_fx([(1, 30.0), (31, 33.0)])]
    period = ReturnPeriod(MarketDate(2025, 1, 1), MarketDate(2025, 1, 31))

    result = calculate_fx_adjusted_return_contribution(
        base_report, period, fx, FxReturnPolicy(FxRateKind("non_cash_buying"), 0)
    )

    comp = result.component_contributions[0]
    assert comp.holding.instrument_id == "INST-1"
    assert abs(comp.security_period_return.return_decimal - 0.1) < 1e-9
    assert abs(comp.effective_base_currency_return - 0.21) < 1e-9
    assert abs(comp.contribution.weighted_contribution - 0.21) < 1e-9


def test_partial_fx_coverage_without_renormalization():
    holdings = [
        HoldingPosition("INST-1", AssetClass("equity"), 0.5),
        HoldingPosition("INST-2", AssetClass("equity"), 0.5),
    ]
    candidates = [
        SecurityPriceHistoryCandidate(
            "INST-1",
            [
                SecurityPriceObservation(
                    "INST-1",
                    MarketDate(2025, 1, 1),
                    UnitPrice(100.0),
                    CurrencyCode("USD"),
                    PriceAdjustment("unadjusted"),
                ),
                SecurityPriceObservation(
                    "INST-1",
                    MarketDate(2025, 1, 31),
                    UnitPrice(110.0),
                    CurrencyCode("USD"),
                    PriceAdjustment("unadjusted"),
                ),
            ],
        ),
        SecurityPriceHistoryCandidate(
            "INST-2",
            [
                SecurityPriceObservation(
                    "INST-2",
                    MarketDate(2025, 1, 1),
                    UnitPrice(100.0),
                    CurrencyCode("EUR"),
                    PriceAdjustment("unadjusted"),
                ),
                SecurityPriceObservation(
                    "INST-2",
                    MarketDate(2025, 1, 31),
                    UnitPrice(110.0),
                    CurrencyCode("EUR"),
                    PriceAdjustment("unadjusted"),
                ),
            ],
        ),
    ]
    policy = AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("unadjusted"),
        MarketDate(2025, 1, 31),
        2,
        0,
    ).with_price_currency_policy(PriceCurrencyPolicy("permit_foreign"))

    report = align_holdings_prices(holdings, candidates, policy)
    period = ReturnPeriod(MarketDate(2025, 1, 1), MarketDate(2025, 1, 31))

    # Provide only USD
    fx = [create_fx([(1, 30.0), (31, 33.0)])]

    result = calculate_fx_adjusted_return_contribution(
        report, period, fx, FxReturnPolicy(FxRateKind("non_cash_buying"), 0)
    )

    assert len(result.component_contributions) == 1
    assert len(result.return_gaps) == 1
    assert abs(result.observed_contribution.observed_contribution - (0.5 * 0.21)) < 1e-9
    assert result.price_coverage == 1.0
    assert result.observed_contribution.return_coverage == 0.5


def test_missing_direct_fx_candidate_typed_context(base_report):
    fx = []  # no candidates
    period = ReturnPeriod(MarketDate(2025, 1, 1), MarketDate(2025, 1, 31))

    result = calculate_fx_adjusted_return_contribution(
        base_report, period, fx, FxReturnPolicy(FxRateKind("non_cash_buying"), 0)
    )

    assert len(result.return_gaps) == 1
    reason = result.return_gaps[0].reason
    assert reason.kind == "missing_direct_fx_candidate"
    assert reason.required_pair == CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    assert reason.required_kind == FxRateKind("non_cash_buying")
    assert reason.requested_date is None


def test_fx_rate_kind_mismatch_pair_required_kind_and_sorted_available_kinds(base_report):
    fx = [
        create_fx([(1, 30.0), (31, 33.0)], kind="cash_selling"),
        create_fx([(1, 30.0), (31, 33.0)], kind="non_cash_selling"),
    ]
    period = ReturnPeriod(MarketDate(2025, 1, 1), MarketDate(2025, 1, 31))

    result = calculate_fx_adjusted_return_contribution(
        base_report, period, fx, FxReturnPolicy(FxRateKind("non_cash_buying"), 0)
    )

    reason = result.return_gaps[0].reason
    assert reason.kind == "fx_rate_kind_mismatch"
    assert reason.required_pair == CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    assert reason.required_kind == FxRateKind("non_cash_buying")
    assert reason.available_kinds == [FxRateKind("non_cash_selling"), FxRateKind("cash_selling")]


def test_missing_stale_start_evidence(base_report):
    # Missing start
    fx = [create_fx([(2, 30.0), (31, 33.0)])]
    period = ReturnPeriod(MarketDate(2025, 1, 1), MarketDate(2025, 1, 31))

    result = calculate_fx_adjusted_return_contribution(
        base_report, period, fx, FxReturnPolicy(FxRateKind("non_cash_buying"), 0)
    )
    reason = result.return_gaps[0].reason
    assert reason.kind == "missing_fx_start_observation"
    assert reason.requested_date == MarketDate(2025, 1, 1)

    # Stale start
    fx = [create_fx([(1, 30.0), (31, 33.0)])]
    period = ReturnPeriod(MarketDate(2025, 1, 5), MarketDate(2025, 1, 31))

    holdings = [HoldingPosition("INST-1", AssetClass("equity"), 1.0)]
    candidates = [
        SecurityPriceHistoryCandidate(
            "INST-1",
            [
                SecurityPriceObservation(
                    "INST-1",
                    MarketDate(2025, 1, 5),
                    UnitPrice(100.0),
                    CurrencyCode("USD"),
                    PriceAdjustment("unadjusted"),
                ),
                SecurityPriceObservation(
                    "INST-1",
                    MarketDate(2025, 1, 31),
                    UnitPrice(110.0),
                    CurrencyCode("USD"),
                    PriceAdjustment("unadjusted"),
                ),
            ],
        )
    ]
    policy = AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("unadjusted"),
        MarketDate(2025, 1, 31),
        2,
        0,
    ).with_price_currency_policy(PriceCurrencyPolicy("permit_foreign"))
    report = align_holdings_prices(holdings, candidates, policy)

    result = calculate_fx_adjusted_return_contribution(
        report, period, fx, FxReturnPolicy(FxRateKind("non_cash_buying"), 1)
    )
    reason = result.return_gaps[0].reason
    assert reason.kind == "stale_fx_start_observation"
    assert reason.boundary_evidence.staleness_calendar_days == 4
    assert reason.maximum_staleness_calendar_days == 1


def test_stale_end_evidence(base_report):
    fx = [create_fx([(1, 30.0), (29, 33.0)])]
    period = ReturnPeriod(MarketDate(2025, 1, 1), MarketDate(2025, 1, 31))

    result = calculate_fx_adjusted_return_contribution(
        base_report, period, fx, FxReturnPolicy(FxRateKind("non_cash_buying"), 1)
    )
    reason = result.return_gaps[0].reason
    assert reason.kind == "stale_fx_end_observation"
    assert reason.boundary_evidence.staleness_calendar_days == 2
    assert reason.maximum_staleness_calendar_days == 1


def test_exact_period_precedence(base_report):
    # Change candidate to start at Jan 2, period asks for Jan 1
    # FX is missing start too. Exact period missing should take precedence.
    holdings = [HoldingPosition("INST-1", AssetClass("equity"), 1.0)]
    candidates = [
        SecurityPriceHistoryCandidate(
            "INST-1",
            [
                SecurityPriceObservation(
                    "INST-1",
                    MarketDate(2025, 1, 2),
                    UnitPrice(100.0),
                    CurrencyCode("USD"),
                    PriceAdjustment("unadjusted"),
                ),
                SecurityPriceObservation(
                    "INST-1",
                    MarketDate(2025, 1, 31),
                    UnitPrice(110.0),
                    CurrencyCode("USD"),
                    PriceAdjustment("unadjusted"),
                ),
            ],
        )
    ]
    policy = AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("unadjusted"),
        MarketDate(2025, 1, 31),
        2,
        0,
    ).with_price_currency_policy(PriceCurrencyPolicy("permit_foreign"))
    report = align_holdings_prices(holdings, candidates, policy)

    fx = [create_fx([(2, 30.0)])]
    period = ReturnPeriod(MarketDate(2025, 1, 1), MarketDate(2025, 1, 31))

    result = calculate_fx_adjusted_return_contribution(
        report, period, fx, FxReturnPolicy(FxRateKind("non_cash_buying"), 0)
    )

    reason = result.return_gaps[0].reason
    assert reason.kind == "missing_exact_period_return"


def test_duplicate_fx_candidates_mapped_to_navlens_validation_error(base_report):
    fx = [create_fx([(1, 30.0), (31, 33.0)]), create_fx([(1, 30.0), (31, 33.0)])]
    period = ReturnPeriod(MarketDate(2025, 1, 1), MarketDate(2025, 1, 31))

    with pytest.raises(NavlensValidationError, match="duplicate FX candidate"):
        calculate_fx_adjusted_return_contribution(
            base_report, period, fx, FxReturnPolicy(FxRateKind("non_cash_buying"), 0)
        )


def test_rejection_of_wrong_wrapper_types(base_report):
    period = ReturnPeriod(MarketDate(2025, 1, 1), MarketDate(2025, 1, 31))

    with pytest.raises(TypeError):
        calculate_fx_adjusted_return_contribution(
            base_report,
            period,
            "not a list of FxRateSeries",
            FxReturnPolicy(FxRateKind("non_cash_buying"), 0),
        )
    with pytest.raises(TypeError):
        calculate_fx_adjusted_return_contribution(
            base_report, period, [123], FxReturnPolicy(FxRateKind("non_cash_buying"), 0)
        )


def test_preservation_of_component_and_gap_ordering():
    holdings = [
        HoldingPosition("INST-2", AssetClass("equity"), 0.5),
        HoldingPosition("INST-1", AssetClass("equity"), 0.5),
    ]
    candidates = [
        SecurityPriceHistoryCandidate(
            "INST-1",
            [
                SecurityPriceObservation(
                    "INST-1",
                    MarketDate(2025, 1, 1),
                    UnitPrice(100.0),
                    CurrencyCode("USD"),
                    PriceAdjustment("unadjusted"),
                ),
                SecurityPriceObservation(
                    "INST-1",
                    MarketDate(2025, 1, 31),
                    UnitPrice(110.0),
                    CurrencyCode("USD"),
                    PriceAdjustment("unadjusted"),
                ),
            ],
        ),
        SecurityPriceHistoryCandidate(
            "INST-2",
            [
                SecurityPriceObservation(
                    "INST-2",
                    MarketDate(2025, 1, 1),
                    UnitPrice(100.0),
                    CurrencyCode("EUR"),
                    PriceAdjustment("unadjusted"),
                ),
                SecurityPriceObservation(
                    "INST-2",
                    MarketDate(2025, 1, 31),
                    UnitPrice(110.0),
                    CurrencyCode("EUR"),
                    PriceAdjustment("unadjusted"),
                ),
            ],
        ),
    ]
    policy = AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("unadjusted"),
        MarketDate(2025, 1, 31),
        2,
        0,
    ).with_price_currency_policy(PriceCurrencyPolicy("permit_foreign"))
    report = align_holdings_prices(holdings, candidates, policy)

    period = ReturnPeriod(MarketDate(2025, 1, 1), MarketDate(2025, 1, 31))
    fx = [create_fx([(1, 30.0), (31, 33.0)])]  # only USD

    result = calculate_fx_adjusted_return_contribution(
        report, period, fx, FxReturnPolicy(FxRateKind("non_cash_buying"), 0)
    )

    # Gaps should follow the holdings order
    assert len(result.return_gaps) == 1
    assert result.return_gaps[0].holding.instrument_id == "INST-2"

    # Components should follow the holdings order
    assert len(result.component_contributions) == 1
    assert result.component_contributions[0].holding.instrument_id == "INST-1"
