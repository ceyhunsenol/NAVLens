use navlens_core::{
    CoreError, DecimalReturn, FundReturnReconciliation, PortfolioComponent,
    PortfolioReturnContribution, PortfolioWeight,
};

fn create_contribution(weight: f64, decimal_return: f64) -> PortfolioReturnContribution {
    let component = PortfolioComponent {
        weight: PortfolioWeight::new(weight).unwrap(),
        market_return: DecimalReturn::new(decimal_return).unwrap(),
    };
    PortfolioReturnContribution::calculate(&[component]).unwrap()
}

#[test]
fn calculates_positive_residual() {
    let published = DecimalReturn::new(0.12).unwrap();
    let contribution = create_contribution(0.8, 0.1);

    let result = FundReturnReconciliation::calculate(published, contribution)
        .expect("should calculate positive residual");

    assert!((result.reconciliation_residual().value() - 0.04).abs() < 1e-12);
}

#[test]
fn calculates_negative_residual() {
    let published = DecimalReturn::new(0.05).unwrap();
    let contribution = create_contribution(0.8, 0.1);

    let result = FundReturnReconciliation::calculate(published, contribution)
        .expect("should calculate negative residual");

    assert!((result.reconciliation_residual().value() - (-0.03)).abs() < 1e-12);
}

#[test]
fn calculates_zero_residual() {
    let published = DecimalReturn::new(0.08).unwrap();
    let contribution = create_contribution(0.8, 0.1);

    let result = FundReturnReconciliation::calculate(published, contribution)
        .expect("should calculate zero residual");

    assert!((result.reconciliation_residual().value() - 0.0).abs() < 1e-12);
}

#[test]
fn preserves_partial_coverage_without_renormalization() {
    let published = DecimalReturn::new(0.12).unwrap();
    let contribution = create_contribution(0.8, 0.1);

    let result = FundReturnReconciliation::calculate(published, contribution).unwrap();

    let observed = result.observed_portfolio_contribution();
    assert!((observed.observed_contribution().value() - 0.08).abs() < 1e-12);
    assert!((observed.return_coverage().value() - 0.8).abs() < 1e-12);
    assert!(!observed.has_full_coverage());
}

#[test]
fn does_not_zero_residual_on_full_coverage() {
    let published = DecimalReturn::new(0.15).unwrap();
    let contribution = create_contribution(1.0, 0.1);

    let result = FundReturnReconciliation::calculate(published, contribution).unwrap();

    assert!(result.observed_portfolio_contribution().has_full_coverage());
    assert!((result.reconciliation_residual().value() - 0.05).abs() < 1e-12);
}

#[test]
fn rejects_non_finite_subtraction_result() {
    let published = DecimalReturn::new(f64::MAX).unwrap();
    let contribution = create_contribution(1.0, -f64::MAX);

    let err = FundReturnReconciliation::calculate(published, contribution)
        .expect_err("should fail with non-finite arithmetic");

    assert!(matches!(err, CoreError::NonFiniteNumber));
}

#[test]
fn getters_return_input_typed_values_unmodified() {
    let published = DecimalReturn::new(0.12).unwrap();
    let contribution = create_contribution(0.8, 0.1);

    let result = FundReturnReconciliation::calculate(published, contribution).unwrap();

    assert_eq!(result.published_fund_return(), published);
    assert_eq!(result.observed_portfolio_contribution(), contribution);
}
