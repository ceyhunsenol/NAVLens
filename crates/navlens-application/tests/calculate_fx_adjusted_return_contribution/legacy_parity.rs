use super::fixtures::{
    align, assert_approximately_equal, candidate, date, fx_series, holding, period,
};
use navlens_application::{
    FxReturnPolicy, PriceCurrencyPolicy, calculate_fx_adjusted_return_contribution,
    calculate_return_contribution,
};
use navlens_core::FxRateKind;

#[test]
fn exact_same_currency_parity_and_irrelevant_fx_candidates_ignored() {
    let holdings = [
        holding("INST-1", 0.4),
        holding("INST-2", 0.6),
        holding("INST-MISSING", 0.0), // no price history provided -> missing gap
    ];
    let candidates = [
        candidate(
            "INST-1",
            "USD",
            &[(date(2025, 1, 1), 100.0), (date(2025, 1, 31), 110.0)],
        ),
        candidate(
            "INST-2",
            "USD",
            &[(date(2025, 1, 1), 50.0), (date(2025, 1, 31), 45.0)],
        ),
    ];

    let report = align(
        &holdings,
        &candidates,
        date(2025, 1, 31),
        "USD", // Fund is USD
        PriceCurrencyPolicy::FundBaseOnly,
    );

    let legacy_result =
        calculate_return_contribution(&report, period(date(2025, 1, 1), date(2025, 1, 31)))
            .expect("legacy calculation should succeed");

    // Irrelevant FX candidates
    let fx = [fx_series(
        "EUR",
        "TRY",
        FxRateKind::NonCashBuying,
        &[(date(2025, 1, 1), 30.0), (date(2025, 1, 31), 33.0)],
    )];

    let fx_policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 0);

    let fx_result = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 1), date(2025, 1, 31)),
        &fx,
        &fx_policy,
    )
    .expect("fx calculation should succeed");

    // Verify ordering, gaps, weights, aggregate
    assert_approximately_equal(
        fx_result
            .observed_contribution()
            .observed_contribution()
            .value(),
        legacy_result
            .observed_contribution()
            .observed_contribution()
            .value(),
    );
    assert_approximately_equal(
        fx_result.price_coverage().value(),
        legacy_result.price_coverage().value(),
    );

    assert_eq!(
        fx_result.return_gaps().len(),
        legacy_result.return_gaps().len(),
    );
    assert_eq!(
        fx_result.component_contributions().len(),
        legacy_result.component_contributions().len(),
    );

    for (i, legacy_comp) in legacy_result.component_contributions().iter().enumerate() {
        let fx_comp = &fx_result.component_contributions()[i];
        assert_eq!(
            fx_comp.holding().instrument_id(),
            legacy_comp.holding().instrument_id()
        );
        assert_approximately_equal(
            fx_comp.effective_base_currency_return().value(),
            legacy_comp.period_return().decimal_return().value(),
        );
        assert_approximately_equal(
            fx_comp.contribution().weighted_contribution().value(),
            legacy_comp.contribution().weighted_contribution().value(),
        );
    }
}
