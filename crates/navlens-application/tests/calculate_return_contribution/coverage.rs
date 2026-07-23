use super::fixtures::{align, assert_approximately_equal, candidate, date, holding};
use navlens_application::{
    CoverageGapReason, ReturnCoverageGapReason, calculate_return_contribution,
};
use navlens_calendar::ReturnPeriod;

#[test]
fn calculates_full_return_coverage() {
    let start = date(2026, 1, 1);
    let end = date(2026, 1, 2);
    let holdings = [holding("A", 0.6), holding("B", 0.4)];
    let candidates = [
        candidate("A", &[(start, 100.0), (end, 105.0)]),
        candidate("B", &[(start, 200.0), (end, 196.0)]),
    ];
    let report = align(&holdings, &candidates, end);
    let period = ReturnPeriod::new(start, end).expect("test period should be valid");

    let result =
        calculate_return_contribution(&report, period).expect("calculation should succeed");

    assert_eq!(result.period(), &period);
    assert_approximately_equal(result.price_coverage().value(), 1.0);
    assert_approximately_equal(
        result.observed_contribution().return_coverage().value(),
        1.0,
    );
    assert_approximately_equal(
        result
            .observed_contribution()
            .observed_contribution()
            .value(),
        0.022,
    );
    assert_eq!(result.component_contributions().len(), 2);
    assert!(result.price_gaps().is_empty());
    assert!(result.return_gaps().is_empty());
}

#[test]
fn preserves_partial_coverage_without_renormalizing() {
    let start = date(2026, 1, 1);
    let end = date(2026, 1, 2);
    let later = date(2026, 1, 3);
    let holdings = [holding("A", 0.5), holding("B", 0.3), holding("C", 0.2)];
    let candidates = [
        candidate("A", &[(start, 100.0), (end, 105.0)]),
        candidate("B", &[(end, 100.0), (later, 110.0)]),
    ];
    let report = align(&holdings, &candidates, later);
    let period = ReturnPeriod::new(start, end).expect("test period should be valid");

    let result =
        calculate_return_contribution(&report, period).expect("calculation should succeed");

    assert_approximately_equal(result.price_coverage().value(), 0.8);
    assert_approximately_equal(
        result.observed_contribution().return_coverage().value(),
        0.5,
    );
    assert_approximately_equal(
        result
            .observed_contribution()
            .observed_contribution()
            .value(),
        0.025,
    );
    assert_eq!(result.price_gaps().len(), 1);
    assert!(matches!(
        result.price_gaps()[0].reason(),
        CoverageGapReason::MissingPriceSeries
    ));
    assert_eq!(result.return_gaps().len(), 1);
    assert_eq!(
        result.return_gaps()[0].reason(),
        &ReturnCoverageGapReason::MissingExactPeriodReturn
    );
}

#[test]
fn rejects_a_different_length_period_as_a_return_gap() {
    let start = date(2026, 1, 1);
    let target_end = date(2026, 1, 2);
    let observed_end = date(2026, 1, 3);
    let holdings = [holding("A", 1.0)];
    let candidates = [candidate("A", &[(start, 100.0), (observed_end, 105.0)])];
    let report = align(&holdings, &candidates, observed_end);
    let period = ReturnPeriod::new(start, target_end).expect("test period should be valid");

    let result =
        calculate_return_contribution(&report, period).expect("calculation should succeed");

    assert_approximately_equal(result.price_coverage().value(), 1.0);
    assert_approximately_equal(
        result.observed_contribution().return_coverage().value(),
        0.0,
    );
    assert_approximately_equal(
        result
            .observed_contribution()
            .observed_contribution()
            .value(),
        0.0,
    );
    assert_eq!(result.return_gaps().len(), 1);
    assert_eq!(
        result.return_gaps()[0].reason(),
        &ReturnCoverageGapReason::MissingExactPeriodReturn
    );
}

#[test]
fn completely_uncovered_report_produces_empty_contribution() {
    let start = date(2026, 1, 1);
    let end = date(2026, 1, 2);
    let holdings = [holding("A", 1.0)];
    let report = align(&holdings, &[], end);
    let period = ReturnPeriod::new(start, end).expect("test period should be valid");

    let result =
        calculate_return_contribution(&report, period).expect("calculation should succeed");

    assert_approximately_equal(result.price_coverage().value(), 0.0);
    assert_approximately_equal(
        result.observed_contribution().return_coverage().value(),
        0.0,
    );
    assert_approximately_equal(
        result
            .observed_contribution()
            .observed_contribution()
            .value(),
        0.0,
    );
    assert_eq!(result.price_gaps().len(), 1);
    assert!(result.return_gaps().is_empty());
}
