use super::fixtures::{
    align, assert_approximately_equal, candidate, date, fx_series, holding, period,
};
use navlens_application::{
    CurrencyReturnAdjustment, FxReturnPolicy, PriceCurrencyPolicy,
    calculate_fx_adjusted_return_contribution,
};
use navlens_core::FxRateKind;

#[test]
fn same_currency_success_without_fx_evidence() {
    let holdings = [holding("INST-1", 1.0)];
    let candidates = [candidate(
        "INST-1",
        "USD",
        &[(date(2025, 1, 1), 100.0), (date(2025, 1, 31), 110.0)],
    )];

    let report = align(
        &holdings,
        &candidates,
        date(2025, 1, 31),
        "USD",
        PriceCurrencyPolicy::FundBaseOnly,
    );

    let fx_policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 0);

    let result = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 1), date(2025, 1, 31)),
        &[], // No FX series needed
        &fx_policy,
    )
    .expect("calculation should succeed");

    assert_eq!(result.component_contributions().len(), 1);
    let comp = &result.component_contributions()[0];

    assert_approximately_equal(comp.effective_base_currency_return().value(), 0.10);
    assert_approximately_equal(comp.contribution().weighted_contribution().value(), 0.10);

    assert!(matches!(
        comp.currency_adjustment(),
        CurrencyReturnAdjustment::NotRequired
    ));
}

#[test]
fn usd_security_gain_and_usd_try_gain_with_multiplicative_interaction() {
    let holdings = [holding("INST-1", 1.0)];
    let candidates = [candidate(
        "INST-1",
        "USD",
        &[(date(2025, 1, 1), 100.0), (date(2025, 1, 31), 110.0)], // +10%
    )];

    let report = align(
        &holdings,
        &candidates,
        date(2025, 1, 31),
        "TRY",
        PriceCurrencyPolicy::PermitForeign,
    );

    let fx = [fx_series(
        "USD",
        "TRY",
        FxRateKind::NonCashBuying,
        &[(date(2025, 1, 1), 30.0), (date(2025, 1, 31), 33.0)], // +10%
    )];

    let fx_policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 0);

    let result = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 1), date(2025, 1, 31)),
        &fx,
        &fx_policy,
    )
    .expect("calculation should succeed");

    assert_eq!(result.component_contributions().len(), 1);
    let comp = &result.component_contributions()[0];

    // (1.10 * 1.10) - 1 = 0.21
    assert_approximately_equal(comp.effective_base_currency_return().value(), 0.21);
    assert_approximately_equal(comp.contribution().weighted_contribution().value(), 0.21);

    match comp.currency_adjustment() {
        CurrencyReturnAdjustment::Applied(ev) => {
            assert_approximately_equal(ev.fx_return().value(), 0.10);
        }
        CurrencyReturnAdjustment::NotRequired => panic!("Expected FX adjustment to be applied"),
    }
}

#[test]
fn security_loss_and_fx_gain() {
    let holdings = [holding("INST-1", 1.0)];
    let candidates = [candidate(
        "INST-1",
        "USD",
        &[(date(2025, 1, 1), 100.0), (date(2025, 1, 31), 90.0)], // -10%
    )];

    let report = align(
        &holdings,
        &candidates,
        date(2025, 1, 31),
        "TRY",
        PriceCurrencyPolicy::PermitForeign,
    );

    let fx = [fx_series(
        "USD",
        "TRY",
        FxRateKind::NonCashBuying,
        &[(date(2025, 1, 1), 30.0), (date(2025, 1, 31), 33.0)], // +10%
    )];

    let fx_policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 0);

    let result = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 1), date(2025, 1, 31)),
        &fx,
        &fx_policy,
    )
    .expect("calculation should succeed");

    assert_eq!(result.component_contributions().len(), 1);
    let comp = &result.component_contributions()[0];

    // (0.90 * 1.10) - 1 = -0.01
    assert_approximately_equal(comp.effective_base_currency_return().value(), -0.01);
    assert_approximately_equal(comp.contribution().weighted_contribution().value(), -0.01);
}

#[test]
fn fx_only_gain_and_fx_only_loss() {
    let holdings = [holding("INST-GAIN", 0.5), holding("INST-LOSS", 0.5)];
    let candidates = [
        candidate(
            "INST-GAIN",
            "USD",
            &[(date(2025, 1, 1), 100.0), (date(2025, 1, 31), 100.0)], // 0%
        ),
        candidate(
            "INST-LOSS",
            "EUR",
            &[(date(2025, 1, 1), 100.0), (date(2025, 1, 31), 100.0)], // 0%
        ),
    ];

    let report = align(
        &holdings,
        &candidates,
        date(2025, 1, 31),
        "TRY",
        PriceCurrencyPolicy::PermitForeign,
    );

    let fx = [
        fx_series(
            "USD",
            "TRY",
            FxRateKind::NonCashBuying,
            &[(date(2025, 1, 1), 30.0), (date(2025, 1, 31), 36.0)], // +20%
        ),
        fx_series(
            "EUR",
            "TRY",
            FxRateKind::NonCashBuying,
            &[(date(2025, 1, 1), 35.0), (date(2025, 1, 31), 31.5)], // -10%
        ),
    ];

    let fx_policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 0);

    let result = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 1), date(2025, 1, 31)),
        &fx,
        &fx_policy,
    )
    .expect("calculation should succeed");

    assert_eq!(result.component_contributions().len(), 2);

    // INST-GAIN
    let gain_comp = result
        .component_contributions()
        .iter()
        .find(|c| c.holding().instrument_id().as_str() == "INST-GAIN")
        .unwrap();
    assert_approximately_equal(gain_comp.effective_base_currency_return().value(), 0.20);
    assert_approximately_equal(
        gain_comp.contribution().weighted_contribution().value(),
        0.10,
    ); // 0.5 * 0.20

    // INST-LOSS
    let loss_comp = result
        .component_contributions()
        .iter()
        .find(|c| c.holding().instrument_id().as_str() == "INST-LOSS")
        .unwrap();
    assert_approximately_equal(loss_comp.effective_base_currency_return().value(), -0.10);
    assert_approximately_equal(
        loss_comp.contribution().weighted_contribution().value(),
        -0.05,
    ); // 0.5 * -0.10

    assert_approximately_equal(
        result
            .observed_contribution()
            .observed_contribution()
            .value(),
        0.05,
    );
}

#[test]
fn effective_return_and_contribution_use_same_scalar() {
    let holdings = [holding("INST-1", 0.5)];
    let candidates = [candidate(
        "INST-1",
        "USD",
        &[(date(2025, 1, 1), 100.0), (date(2025, 1, 31), 110.0)],
    )];

    let report = align(
        &holdings,
        &candidates,
        date(2025, 1, 31),
        "TRY",
        PriceCurrencyPolicy::PermitForeign,
    );

    let fx = [fx_series(
        "USD",
        "TRY",
        FxRateKind::NonCashBuying,
        &[(date(2025, 1, 1), 30.0), (date(2025, 1, 31), 33.0)],
    )];

    let fx_policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 0);

    let result = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 1), date(2025, 1, 31)),
        &fx,
        &fx_policy,
    )
    .expect("calculation should succeed");

    let comp = &result.component_contributions()[0];

    let effective = comp.effective_base_currency_return();
    let weight: f64 = comp.holding().fund_total_weight().value();
    let contribution: f64 = comp.contribution().weighted_contribution().value();

    assert_approximately_equal(weight * effective.value(), contribution);
}

#[test]
fn partial_fx_coverage_without_renormalization() {
    let holdings = [holding("INST-COV", 0.6), holding("INST-UNCOV", 0.4)];
    let candidates = [
        candidate(
            "INST-COV",
            "USD",
            &[(date(2025, 1, 1), 100.0), (date(2025, 1, 31), 110.0)],
        ),
        candidate(
            "INST-UNCOV",
            "EUR",
            &[(date(2025, 1, 1), 100.0), (date(2025, 1, 31), 110.0)],
        ),
    ];

    let report = align(
        &holdings,
        &candidates,
        date(2025, 1, 31),
        "TRY",
        PriceCurrencyPolicy::PermitForeign,
    );

    // Only USD/TRY is provided. EUR/TRY is missing.
    let fx = [fx_series(
        "USD",
        "TRY",
        FxRateKind::NonCashBuying,
        &[(date(2025, 1, 1), 30.0), (date(2025, 1, 31), 33.0)],
    )];

    let fx_policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 0);

    let result = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 1), date(2025, 1, 31)),
        &fx,
        &fx_policy,
    )
    .expect("calculation should succeed");

    assert_eq!(result.component_contributions().len(), 1); // Only INST-COV

    assert_eq!(result.return_gaps().len(), 1); // INST-UNCOV gap

    // Total contribution is just 0.6 weight * 0.21 return = 0.126. It is NOT renormalized.
    assert_approximately_equal(
        result
            .observed_contribution()
            .observed_contribution()
            .value(),
        0.126,
    );
}

#[test]
fn successful_components_preserve_holding_order() {
    let holdings = [holding("SECOND", 0.5), holding("FIRST", 0.5)];
    let candidates = [
        candidate(
            "SECOND",
            "USD",
            &[(date(2025, 1, 1), 100.0), (date(2025, 1, 31), 101.0)],
        ),
        candidate(
            "FIRST",
            "USD",
            &[(date(2025, 1, 1), 100.0), (date(2025, 1, 31), 102.0)],
        ),
    ];
    let report = align(
        &holdings,
        &candidates,
        date(2025, 1, 31),
        "USD",
        PriceCurrencyPolicy::FundBaseOnly,
    );
    let result = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 1), date(2025, 1, 31)),
        &[],
        &FxReturnPolicy::new(FxRateKind::NonCashBuying, 0),
    )
    .expect("same-currency calculation should succeed");

    let identifiers: Vec<_> = result
        .component_contributions()
        .iter()
        .map(|component| component.holding().instrument_id().as_str())
        .collect();
    assert_eq!(identifiers, ["SECOND", "FIRST"]);
}
