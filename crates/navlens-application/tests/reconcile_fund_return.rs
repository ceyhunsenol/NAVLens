#[path = "calculate_return_contribution/fixtures.rs"]
mod fixtures;
#[allow(dead_code)]
#[path = "calculate_fx_adjusted_return_contribution/fixtures.rs"]
mod fx_fixtures;

use fixtures::{align, assert_approximately_equal, candidate, date, holding};
use navlens_application::{
    ReconcileFundReturnError, ReturnContributionResult, calculate_return_contribution,
    reconcile_fund_return,
};
use navlens_calendar::{PeriodDecimalReturn, ReturnPeriod};
use navlens_core::{CoreError, DecimalReturn};
use std::error::Error;

fn setup_valid_contribution(target_period: ReturnPeriod) -> ReturnContributionResult {
    let prices = vec![
        (target_period.period_start_date(), 100.0),
        (target_period.period_end_date(), 110.0),
    ];
    let holdings = vec![holding("AAPL", 0.8)];
    let candidates = vec![candidate("AAPL", &prices)];
    let report = align(&holdings, &candidates, target_period.period_end_date());
    calculate_return_contribution(&report, target_period).unwrap()
}

#[test]
fn exact_period_success_calculates_residual() {
    let start = date(2026, 1, 30);
    let end = date(2026, 1, 31);
    let target_period = ReturnPeriod::new(start, end).unwrap();

    let published =
        PeriodDecimalReturn::new(start, end, DecimalReturn::new(0.12).unwrap()).unwrap();
    let contribution = setup_valid_contribution(target_period);

    let result =
        reconcile_fund_return(published, &contribution).expect("should reconcile successfully");

    assert_eq!(result.period(), target_period);
    assert_approximately_equal(
        result.reconciliation().reconciliation_residual().value(),
        0.04,
    );
}

#[test]
fn rejects_period_mismatch() {
    let start1 = date(2026, 1, 30);
    let end1 = date(2026, 1, 31);
    let period1 = ReturnPeriod::new(start1, end1).unwrap();

    let start2 = date(2026, 1, 29);
    let end2 = date(2026, 1, 31);
    let period2 = ReturnPeriod::new(start2, end2).unwrap();

    let published =
        PeriodDecimalReturn::new(start1, end1, DecimalReturn::new(0.12).unwrap()).unwrap();
    let contribution = setup_valid_contribution(period2);

    let err = reconcile_fund_return(published, &contribution)
        .expect_err("should fail with period mismatch");

    assert_eq!(
        err,
        ReconcileFundReturnError::PeriodMismatch {
            published_period: period1,
            contribution_period: period2,
        }
    );
    assert!(err.source().is_none());
}

#[test]
fn preserves_partial_coverage_without_renormalization() {
    let start = date(2026, 1, 30);
    let end = date(2026, 1, 31);
    let target_period = ReturnPeriod::new(start, end).unwrap();

    let published =
        PeriodDecimalReturn::new(start, end, DecimalReturn::new(0.12).unwrap()).unwrap();
    let contribution = setup_valid_contribution(target_period);

    let result = reconcile_fund_return(published, &contribution).unwrap();

    let observed = result.reconciliation().observed_portfolio_contribution();
    assert_approximately_equal(observed.observed_contribution().value(), 0.08);
    assert_approximately_equal(observed.return_coverage().value(), 0.8);
}

#[test]
fn does_not_zero_residual_on_full_coverage() {
    let start = date(2026, 1, 30);
    let end = date(2026, 1, 31);
    let target_period = ReturnPeriod::new(start, end).unwrap();

    let prices = vec![(start, 100.0), (end, 110.0)];
    let holdings = vec![holding("AAPL", 1.0)];
    let candidates = vec![candidate("AAPL", &prices)];
    let report = align(&holdings, &candidates, end);
    let contribution = calculate_return_contribution(&report, target_period).unwrap();

    let published =
        PeriodDecimalReturn::new(start, end, DecimalReturn::new(0.15).unwrap()).unwrap();

    let result = reconcile_fund_return(published, &contribution).unwrap();

    assert!(
        result
            .reconciliation()
            .observed_portfolio_contribution()
            .has_full_coverage()
    );
    assert_approximately_equal(
        result.reconciliation().reconciliation_residual().value(),
        0.05,
    );
}

#[test]
fn propagates_core_domain_error_for_non_finite_subtraction() {
    let start = date(2026, 1, 30);
    let end = date(2026, 1, 31);
    let target_period = ReturnPeriod::new(start, end).unwrap();

    let prices = vec![(start, 1e-154), (end, 1e154)];
    let holdings = vec![holding("AAPL", 1.0)];
    let candidates = vec![candidate("AAPL", &prices)];
    let report = align(&holdings, &candidates, end);
    let contribution = calculate_return_contribution(&report, target_period).unwrap();

    let published =
        PeriodDecimalReturn::new(start, end, DecimalReturn::new(-1e308).unwrap()).unwrap();

    let err = reconcile_fund_return(published, &contribution)
        .expect_err("should fail with non-finite subtraction");

    assert_eq!(
        err,
        ReconcileFundReturnError::Domain(CoreError::NonFiniteNumber)
    );
    assert_eq!(
        err.source()
            .and_then(|source| source.downcast_ref::<CoreError>()),
        Some(&CoreError::NonFiniteNumber)
    );
}

#[test]
fn produces_identical_results_for_identical_typed_inputs() {
    let start = date(2026, 1, 30);
    let end = date(2026, 1, 31);
    let target_period = ReturnPeriod::new(start, end).unwrap();
    let published =
        PeriodDecimalReturn::new(start, end, DecimalReturn::new(0.12).unwrap()).unwrap();
    let contribution = setup_valid_contribution(target_period);

    let first = reconcile_fund_return(published, &contribution).unwrap();
    let second = reconcile_fund_return(published, &contribution).unwrap();

    assert_eq!(first, second);
}

fn setup_valid_fx_contribution(
    target_period: ReturnPeriod,
) -> navlens_application::FxAdjustedReturnContributionResult {
    setup_fx_contribution(target_period, 100.0, 110.0, 0.8, 30.0, 33.0)
}

fn setup_fx_contribution(
    target_period: ReturnPeriod,
    start_price: f64,
    end_price: f64,
    weight: f64,
    start_fx_rate: f64,
    end_fx_rate: f64,
) -> navlens_application::FxAdjustedReturnContributionResult {
    let prices = [
        (target_period.period_start_date(), start_price),
        (target_period.period_end_date(), end_price),
    ];
    let holdings = [fx_fixtures::holding("AAPL", weight)];
    let candidates = [fx_fixtures::candidate("AAPL", "USD", &prices)];
    let report = fx_fixtures::align(
        &holdings,
        &candidates,
        target_period.period_end_date(),
        "TRY",
        navlens_application::PriceCurrencyPolicy::PermitForeign,
    );
    let fx = [fx_fixtures::fx_series(
        "USD",
        "TRY",
        navlens_core::FxRateKind::NonCashBuying,
        &[
            (target_period.period_start_date(), start_fx_rate),
            (target_period.period_end_date(), end_fx_rate),
        ],
    )];
    let fx_policy =
        navlens_application::FxReturnPolicy::new(navlens_core::FxRateKind::NonCashBuying, 0);
    navlens_application::calculate_fx_adjusted_return_contribution(
        &report,
        target_period,
        &fx,
        &fx_policy,
    )
    .unwrap()
}

#[test]
fn fx_exact_period_success_calculates_residual() {
    let start = date(2026, 1, 30);
    let end = date(2026, 1, 31);
    let target_period = ReturnPeriod::new(start, end).unwrap();

    let published =
        PeriodDecimalReturn::new(start, end, DecimalReturn::new(0.20).unwrap()).unwrap();
    let contribution = setup_valid_fx_contribution(target_period);

    let result = navlens_application::reconcile_fx_adjusted_fund_return(published, &contribution)
        .expect("should reconcile FX result successfully");

    assert_eq!(result.period(), target_period);
    assert_approximately_equal(
        result.reconciliation().reconciliation_residual().value(),
        0.032,
    );
}

#[test]
fn fx_residual_signs_are_canonical() {
    let start = date(2026, 1, 30);
    let end = date(2026, 1, 31);
    let target_period = ReturnPeriod::new(start, end).unwrap();
    let contribution = setup_valid_fx_contribution(target_period);

    for (published_value, expected_residual) in [(0.20, 0.032), (0.10, -0.068), (0.168, 0.0)] {
        let published =
            PeriodDecimalReturn::new(start, end, DecimalReturn::new(published_value).unwrap())
                .unwrap();
        let result =
            navlens_application::reconcile_fx_adjusted_fund_return(published, &contribution)
                .unwrap();

        assert_approximately_equal(
            result.reconciliation().reconciliation_residual().value(),
            expected_residual,
        );
    }
}

#[test]
fn fx_rejects_period_mismatch() {
    let start1 = date(2026, 1, 30);
    let end1 = date(2026, 1, 31);
    let period1 = ReturnPeriod::new(start1, end1).unwrap();

    let start2 = date(2026, 1, 29);
    let end2 = date(2026, 1, 31);
    let period2 = ReturnPeriod::new(start2, end2).unwrap();

    let published =
        PeriodDecimalReturn::new(start1, end1, DecimalReturn::new(0.12).unwrap()).unwrap();
    let contribution = setup_valid_fx_contribution(period2);

    let err = navlens_application::reconcile_fx_adjusted_fund_return(published, &contribution)
        .expect_err("should fail with period mismatch");

    assert_eq!(
        err,
        ReconcileFundReturnError::PeriodMismatch {
            published_period: period1,
            contribution_period: period2,
        }
    );
}

#[test]
fn fx_preserves_partial_coverage_without_renormalization() {
    let start = date(2026, 1, 30);
    let end = date(2026, 1, 31);
    let target_period = ReturnPeriod::new(start, end).unwrap();

    let published =
        PeriodDecimalReturn::new(start, end, DecimalReturn::new(0.12).unwrap()).unwrap();
    let contribution = setup_valid_fx_contribution(target_period);

    let result =
        navlens_application::reconcile_fx_adjusted_fund_return(published, &contribution).unwrap();

    let observed = result.reconciliation().observed_portfolio_contribution();
    assert_approximately_equal(observed.observed_contribution().value(), 0.168);
    assert_approximately_equal(observed.return_coverage().value(), 0.8);
}

#[test]
fn fx_propagates_core_domain_error_for_non_finite_subtraction() {
    let start = date(2026, 1, 30);
    let end = date(2026, 1, 31);
    let target_period = ReturnPeriod::new(start, end).unwrap();
    let contribution = setup_fx_contribution(target_period, 1e-154, 1e154, 1.0, 30.0, 30.0);
    let published =
        PeriodDecimalReturn::new(start, end, DecimalReturn::new(-1e308).unwrap()).unwrap();

    let error = navlens_application::reconcile_fx_adjusted_fund_return(published, &contribution)
        .expect_err("should reject non-finite residual subtraction");

    assert_eq!(
        error,
        ReconcileFundReturnError::Domain(CoreError::NonFiniteNumber)
    );
}

#[test]
fn legacy_and_fx_aware_inputs_parity() {
    let start = date(2026, 1, 30);
    let end = date(2026, 1, 31);
    let target_period = ReturnPeriod::new(start, end).unwrap();

    let published =
        PeriodDecimalReturn::new(start, end, DecimalReturn::new(0.12).unwrap()).unwrap();
    let legacy_prices = vec![(start, 100.0), (end, 150.0)];
    let legacy_holdings = vec![holding("AAPL", 0.5)];
    let legacy_candidates = vec![candidate("AAPL", &legacy_prices)];
    let legacy_report = align(&legacy_holdings, &legacy_candidates, end);
    let legacy_contrib = calculate_return_contribution(&legacy_report, target_period).unwrap();
    let fx_contrib = setup_fx_contribution(target_period, 100.0, 150.0, 0.5, 30.0, 30.0);

    let legacy_result = reconcile_fund_return(published, &legacy_contrib).unwrap();
    let fx_result =
        navlens_application::reconcile_fx_adjusted_fund_return(published, &fx_contrib).unwrap();

    assert_eq!(legacy_result, fx_result);
}
