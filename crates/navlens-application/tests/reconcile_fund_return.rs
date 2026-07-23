#[path = "calculate_return_contribution/fixtures.rs"]
mod fixtures;

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
