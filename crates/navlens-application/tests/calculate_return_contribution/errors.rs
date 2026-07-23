use super::fixtures::{align, candidate, date, holding};
use navlens_application::{CalculateReturnContributionError, calculate_return_contribution};
use navlens_calendar::{PricingError, ReturnPeriod};
use navlens_core::CoreError;

#[test]
fn preserves_pricing_error_conversion() {
    let pricing_error = PricingError::InvalidReturnPeriod {
        period_start_date: date(2026, 1, 2),
        period_end_date: date(2026, 1, 1),
    };

    assert_eq!(
        CalculateReturnContributionError::from(pricing_error.clone()),
        CalculateReturnContributionError::Pricing(pricing_error)
    );
}

#[test]
fn preserves_core_error_conversion() {
    assert_eq!(
        CalculateReturnContributionError::from(CoreError::EmptyPortfolio),
        CalculateReturnContributionError::Domain(CoreError::EmptyPortfolio)
    );
}

#[test]
fn propagates_pricing_error_from_the_use_case() {
    let start = date(2026, 1, 1);
    let end = date(2026, 1, 2);
    let holdings = [holding("A", 1.0)];
    let candidates = [candidate(
        "A",
        &[(start, f64::MIN_POSITIVE), (end, f64::MAX)],
    )];
    let report = align(&holdings, &candidates, end);
    let period = ReturnPeriod::new(start, end).expect("test period should be valid");

    let error =
        calculate_return_contribution(&report, period).expect_err("non-finite return should fail");

    assert_eq!(
        error,
        CalculateReturnContributionError::Pricing(PricingError::ReturnCalculation(
            CoreError::NonFiniteNumber
        ))
    );
}
