use super::fixtures::{align, candidate, date, fx_series, holding, period};
use navlens_application::{
    CalculateReturnContributionError, FxReturnPolicy, PriceCurrencyPolicy, ReturnCoverageGapReason,
    calculate_fx_adjusted_return_contribution,
};
use navlens_core::FxRateKind;

#[test]
fn duplicate_pair_kind_is_fatal_before_holding_processing() {
    let report = align(
        &[],
        &[],
        date(2025, 1, 31),
        "TRY",
        PriceCurrencyPolicy::PermitForeign,
    );

    let fx = [
        fx_series(
            "USD",
            "TRY",
            FxRateKind::NonCashBuying,
            &[(date(2025, 1, 1), 30.0)],
        ),
        fx_series(
            "USD",
            "TRY",
            FxRateKind::NonCashBuying,
            &[(date(2025, 1, 2), 31.0)],
        ),
    ];

    let fx_policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 0);

    let err = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 1), date(2025, 1, 31)),
        &fx,
        &fx_policy,
    )
    .expect_err("should fail with duplicate candidate");

    assert!(matches!(
        err,
        CalculateReturnContributionError::DuplicateFxCandidate { .. }
    ));
}

#[test]
fn duplicate_detection_is_input_order_independent() {
    let report = align(
        &[],
        &[],
        date(2025, 1, 31),
        "TRY",
        PriceCurrencyPolicy::PermitForeign,
    );
    let first = fx_series(
        "USD",
        "TRY",
        FxRateKind::NonCashBuying,
        &[(date(2025, 1, 1), 30.0)],
    );
    let second = fx_series(
        "USD",
        "TRY",
        FxRateKind::NonCashBuying,
        &[(date(2025, 1, 2), 31.0)],
    );
    let target = period(date(2025, 1, 1), date(2025, 1, 31));
    let policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 0);

    let forward = calculate_fx_adjusted_return_contribution(
        &report,
        target,
        &[first.clone(), second.clone()],
        &policy,
    )
    .expect_err("duplicate candidates should fail");
    let reverse =
        calculate_fx_adjusted_return_contribution(&report, target, &[second, first], &policy)
            .expect_err("reversed duplicate candidates should fail");

    assert_eq!(forward, reverse);
}

#[test]
fn reverse_only_pair_gives_missing_direct_fx_candidate() {
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
        "TRY",
        PriceCurrencyPolicy::PermitForeign,
    );

    // Provide TRY/USD instead of USD/TRY
    let fx = [fx_series(
        "TRY",
        "USD",
        FxRateKind::NonCashBuying,
        &[(date(2025, 1, 1), 0.033)],
    )];
    let fx_policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 0);

    let result = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 1), date(2025, 1, 31)),
        &fx,
        &fx_policy,
    )
    .expect("calculation should succeed");

    assert_eq!(result.return_gaps().len(), 1);
    assert!(matches!(
        result.return_gaps()[0].reason(),
        ReturnCoverageGapReason::MissingDirectFxCandidate { .. }
    ));
}

#[test]
fn wrong_kinds_give_fx_rate_kind_mismatch_and_available_kinds_are_sorted() {
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
        "TRY",
        PriceCurrencyPolicy::PermitForeign,
    );

    let fx = [
        fx_series(
            "USD",
            "TRY",
            FxRateKind::CashSelling,
            &[(date(2025, 1, 1), 30.0)],
        ),
        fx_series(
            "USD",
            "TRY",
            FxRateKind::NonCashSelling,
            &[(date(2025, 1, 1), 30.0)],
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

    let gaps = result.return_gaps();
    assert_eq!(gaps.len(), 1);
    match gaps[0].reason() {
        ReturnCoverageGapReason::FxRateKindMismatch {
            available_kinds, ..
        } => {
            assert_eq!(
                available_kinds.as_slice(),
                &[FxRateKind::NonCashSelling, FxRateKind::CashSelling]
            );
        }
        _ => panic!("Expected FxRateKindMismatch"),
    }
}

#[test]
fn missing_start() {
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
        "TRY",
        PriceCurrencyPolicy::PermitForeign,
    );

    let fx = [fx_series(
        "USD",
        "TRY",
        FxRateKind::NonCashBuying,
        &[(date(2025, 1, 2), 30.0)],
    )];
    let fx_policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 0);

    let result = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 1), date(2025, 1, 31)),
        &fx,
        &fx_policy,
    )
    .unwrap();

    assert!(matches!(
        result.return_gaps()[0].reason(),
        ReturnCoverageGapReason::MissingFxStartObservation { .. }
    ));
}

#[test]
fn stale_start_produces_a_typed_gap() {
    let holdings = [holding("INST-1", 1.0)];
    let candidates = [candidate(
        "INST-1",
        "USD",
        &[(date(2025, 1, 5), 100.0), (date(2025, 1, 31), 110.0)],
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
        &[(date(2025, 1, 1), 30.0), (date(2025, 1, 31), 31.0)],
    )];

    let fx_policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 3);
    let result = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 5), date(2025, 1, 31)),
        &fx,
        &fx_policy,
    )
    .unwrap();

    assert_eq!(result.return_gaps().len(), 1);
    assert!(matches!(
        result.return_gaps()[0].reason(),
        ReturnCoverageGapReason::StaleFxStartObservation { .. }
    ));
}

#[test]
fn inclusive_start_staleness_boundary_succeeds() {
    let holdings = [holding("INST-1", 1.0)];
    let candidates = [candidate(
        "INST-1",
        "USD",
        &[(date(2025, 1, 4), 100.0), (date(2025, 1, 31), 110.0)],
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
        &[(date(2025, 1, 1), 30.0), (date(2025, 1, 31), 31.0)],
    )];
    let result = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 4), date(2025, 1, 31)),
        &fx,
        &FxReturnPolicy::new(FxRateKind::NonCashBuying, 3),
    )
    .expect("inclusive staleness boundary should succeed");

    assert_eq!(result.component_contributions().len(), 1);
    assert!(result.return_gaps().is_empty());
}

#[test]
fn requested_and_actual_evidence_dates_preserved() {
    let holdings = [holding("INST-1", 1.0)];
    let candidates = [candidate(
        "INST-1",
        "USD",
        &[(date(2025, 1, 5), 100.0), (date(2025, 1, 31), 110.0)],
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
        &[(date(2025, 1, 4), 30.0), (date(2025, 1, 30), 31.0)],
    )];
    let fx_policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 1); // 1 day allowed

    let result = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 5), date(2025, 1, 31)),
        &fx,
        &fx_policy,
    )
    .unwrap();

    let comp = &result.component_contributions()[0];
    if let navlens_application::CurrencyReturnAdjustment::Applied(ev) = comp.currency_adjustment() {
        assert_eq!(ev.start().requested_date(), date(2025, 1, 5));
        assert_eq!(ev.start().observation().market_date(), date(2025, 1, 4));
        assert_eq!(ev.end().requested_date(), date(2025, 1, 31));
        assert_eq!(ev.end().observation().market_date(), date(2025, 1, 30));
    } else {
        panic!("Expected Applied adjustment");
    }
}

#[test]
fn missing_exact_period_return_precedes_every_fx_gap_and_order_preserved() {
    let holdings = [
        holding("INST-1", 0.5), // Valid
        holding("INST-2", 0.5), // Missing period return
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
            &[(date(2025, 1, 2), 100.0), (date(2025, 1, 31), 110.0)],
        ),
    ];
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
        &[(date(2025, 1, 2), 30.0)],
    )];
    let fx_policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 0);

    let result = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 1), date(2025, 1, 31)),
        &fx,
        &fx_policy,
    )
    .unwrap();

    assert_eq!(result.return_gaps().len(), 2);

    // INST-1 fails on FX start gap because rate is on Jan 2, but needs Jan 1
    assert_eq!(
        result.return_gaps()[0].holding().instrument_id().as_str(),
        "INST-1"
    );
    assert!(matches!(
        result.return_gaps()[0].reason(),
        ReturnCoverageGapReason::MissingFxStartObservation { .. }
    ));

    // INST-2 fails on MissingExactPeriodReturn before any FX gap because period is 1 to 31, but it only has 2 to 31
    assert_eq!(
        result.return_gaps()[1].holding().instrument_id().as_str(),
        "INST-2"
    );
    assert!(matches!(
        result.return_gaps()[1].reason(),
        ReturnCoverageGapReason::MissingExactPeriodReturn
    ));
}

#[test]
fn stale_end() {
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
        "TRY",
        PriceCurrencyPolicy::PermitForeign,
    );

    let fx = [fx_series(
        "USD",
        "TRY",
        FxRateKind::NonCashBuying,
        &[(date(2025, 1, 1), 30.0), (date(2025, 1, 29), 31.0)],
    )];
    let fx_policy = FxReturnPolicy::new(FxRateKind::NonCashBuying, 1);

    let result = calculate_fx_adjusted_return_contribution(
        &report,
        period(date(2025, 1, 1), date(2025, 1, 31)),
        &fx,
        &fx_policy,
    )
    .unwrap();

    assert!(matches!(
        result.return_gaps()[0].reason(),
        ReturnCoverageGapReason::StaleFxEndObservation { .. }
    ));
}
