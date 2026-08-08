use navlens_backtest::{
    BacktestError, ReconciliationObservation, ReconciliationSeries, evaluate_reconciliations,
};
use navlens_calendar::{MarketDate, ReturnPeriod};
use navlens_core::{
    DecimalReturn, FundReturnReconciliation, PortfolioComponent, PortfolioReturnContribution,
    PortfolioWeight,
};

fn make_period(start_day: u8, end_day: u8) -> ReturnPeriod {
    ReturnPeriod::new(
        MarketDate::new(2026, 1, start_day).unwrap(),
        MarketDate::new(2026, 1, end_day).unwrap(),
    )
    .unwrap()
}

fn make_reconciliation(published: f64, observed: f64, weight: f64) -> FundReturnReconciliation {
    let published_ret = DecimalReturn::new(published).unwrap();
    let comp = PortfolioComponent {
        weight: PortfolioWeight::new(weight).unwrap(),
        market_return: DecimalReturn::new(observed / weight).unwrap(),
    };
    let contrib = PortfolioReturnContribution::calculate(&[comp]).unwrap();
    FundReturnReconciliation::calculate(published_ret, contrib).unwrap()
}

#[test]
fn evaluates_exact_metrics_for_positive_negative_and_zero_residuals() {
    let p1 = make_period(1, 2);
    let p2 = make_period(2, 3);
    let p3 = make_period(3, 4);

    // residual 1 = 0.10 - 0.08 = +0.02, full coverage
    let r1 = make_reconciliation(0.10, 0.08, 1.0);
    // residual 2 = 0.05 - 0.09 = -0.04, partial coverage 0.5
    let r2 = make_reconciliation(0.05, 0.09, 0.5);
    // residual 3 = 0.03 - 0.03 = 0.00, full coverage
    let r3 = make_reconciliation(0.03, 0.03, 1.0);

    let obs1 = ReconciliationObservation::new(p1, r1);
    let obs2 = ReconciliationObservation::new(p2, r2);
    let obs3 = ReconciliationObservation::new(p3, r3);

    let series = ReconciliationSeries::new(vec![obs1, obs2, obs3]).unwrap();
    let metrics = evaluate_reconciliations(&series);

    assert_eq!(metrics.sample_count(), 3);
    // residuals: +0.02, -0.04, 0.00
    // MAE = (|0.02| + |-0.04| + |0.00|) / 3 = 0.06 / 3 = 0.02
    assert!((metrics.mean_absolute_residual() - 0.02).abs() < 1e-9);
    // mean residual = (0.02 - 0.04 + 0.00) / 3 = -0.02 / 3
    assert!((metrics.mean_residual() - (-0.02 / 3.0)).abs() < 1e-9);
    // RMSE = sqrt((0.02^2 + (-0.04)^2 + 0.00^2) / 3) = sqrt((0.0004 + 0.0016) / 3) = sqrt(0.0020 / 3)
    let expected_rmse = (0.0020 / 3.0_f64).sqrt();
    assert!((metrics.root_mean_squared_residual() - expected_rmse).abs() < 1e-9);
    // mean return coverage = (1.0 + 0.5 + 1.0) / 3 = 2.5 / 3
    assert!((metrics.mean_return_coverage() - (2.5 / 3.0)).abs() < 1e-9);
    // full coverage count = 2 (obs1, obs3), ratio = 2/3
    assert!((metrics.full_return_coverage_ratio() - (2.0 / 3.0)).abs() < 1e-9);
}

#[test]
fn evaluates_single_observation() {
    let p1 = make_period(1, 2);
    let r1 = make_reconciliation(0.05, 0.03, 1.0);
    let obs1 = ReconciliationObservation::new(p1, r1);

    let series = ReconciliationSeries::new(vec![obs1]).unwrap();
    let metrics = evaluate_reconciliations(&series);

    assert_eq!(metrics.sample_count(), 1);
    assert!((metrics.mean_absolute_residual() - 0.02).abs() < 1e-9);
    assert!((metrics.mean_residual() - 0.02).abs() < 1e-9);
    assert!((metrics.root_mean_squared_residual() - 0.02).abs() < 1e-9);
    assert!((metrics.mean_return_coverage() - 1.0).abs() < 1e-9);
    assert!((metrics.full_return_coverage_ratio() - 1.0).abs() < 1e-9);
}

#[test]
fn rejects_empty_reconciliation_series() {
    let err = ReconciliationSeries::new(vec![]).unwrap_err();
    assert_eq!(err, BacktestError::NoReconciliationObservations);
}

#[test]
fn rejects_duplicate_reconciliation_period() {
    let p1 = make_period(1, 2);
    let r1 = make_reconciliation(0.05, 0.03, 1.0);
    let obs1 = ReconciliationObservation::new(p1, r1);
    let obs2 = ReconciliationObservation::new(p1, r1);

    let err = ReconciliationSeries::new(vec![obs1, obs2]).unwrap_err();
    assert_eq!(err, BacktestError::DuplicateReconciliationPeriod(p1));
}

#[test]
fn duplicate_period_precedes_chronology_error_when_not_adjacent() {
    let p1 = make_period(1, 2);
    let p2 = make_period(2, 3);
    let reconciliation = make_reconciliation(0.05, 0.03, 1.0);

    let error = ReconciliationSeries::new(vec![
        ReconciliationObservation::new(p1, reconciliation),
        ReconciliationObservation::new(p2, reconciliation),
        ReconciliationObservation::new(p1, reconciliation),
    ])
    .unwrap_err();

    assert_eq!(error, BacktestError::DuplicateReconciliationPeriod(p1));
}

#[test]
fn rejects_decreasing_or_non_increasing_period_end_dates() {
    let p1 = make_period(1, 3);
    let p2 = make_period(2, 3); // same end date 3
    let r1 = make_reconciliation(0.05, 0.03, 1.0);

    let obs1 = ReconciliationObservation::new(p1, r1);
    let obs2 = ReconciliationObservation::new(p2, r1);

    let err = ReconciliationSeries::new(vec![obs1, obs2]).unwrap_err();
    assert_eq!(
        err,
        BacktestError::NonChronologicalReconciliationPeriod {
            previous: MarketDate::new(2026, 1, 3).unwrap(),
            current: MarketDate::new(2026, 1, 3).unwrap(),
        }
    );

    let p3_early = make_period(1, 2); // end date 2 < 3
    let obs3 = ReconciliationObservation::new(p3_early, r1);
    let err2 = ReconciliationSeries::new(vec![obs1, obs3]).unwrap_err();
    assert_eq!(
        err2,
        BacktestError::NonChronologicalReconciliationPeriod {
            previous: MarketDate::new(2026, 1, 3).unwrap(),
            current: MarketDate::new(2026, 1, 2).unwrap(),
        }
    );
}

#[test]
fn preserves_input_order() {
    let p1 = make_period(1, 2);
    let p2 = make_period(2, 3);
    let r1 = make_reconciliation(0.05, 0.03, 1.0);
    let r2 = make_reconciliation(0.08, 0.04, 1.0);

    let obs1 = ReconciliationObservation::new(p1, r1);
    let obs2 = ReconciliationObservation::new(p2, r2);

    let series = ReconciliationSeries::new(vec![obs1, obs2]).unwrap();
    assert_eq!(series.observations()[0], obs1);
    assert_eq!(series.observations()[1], obs2);
}

#[test]
fn parity_between_reconciliations_with_equal_canonical_values() {
    let p1 = make_period(1, 2);
    let r1 = make_reconciliation(0.05, 0.03, 1.0);
    let r2 = make_reconciliation(0.05, 0.03, 1.0);

    let obs1 = ReconciliationObservation::new(p1, r1);
    let obs2 = ReconciliationObservation::new(p1, r2);

    let series1 = ReconciliationSeries::new(vec![obs1]).unwrap();
    let series2 = ReconciliationSeries::new(vec![obs2]).unwrap();

    let m1 = evaluate_reconciliations(&series1);
    let m2 = evaluate_reconciliations(&series2);

    assert_eq!(m1, m2);
}
