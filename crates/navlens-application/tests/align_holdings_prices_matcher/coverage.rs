use super::fixtures::{candidate, date, holding, instrument, policy};
use navlens_application::{CoverageGapReason, align_holdings_prices};
use navlens_calendar::PriceAdjustment;
use navlens_core::AssetClass;

#[test]
fn reports_full_coverage() {
    let equity = instrument("EQUITY");
    let etf = instrument("ETF");
    let holdings = vec![
        holding(&equity, AssetClass::Equity, 0.4),
        holding(&etf, AssetClass::ExchangeTradedFund, 0.6),
    ];
    let candidates = vec![
        candidate(
            &equity,
            &[date(2026, 7, 9), date(2026, 7, 10)],
            "USD",
            PriceAdjustment::TotalReturnAdjusted,
        ),
        candidate(
            &etf,
            &[date(2026, 7, 9), date(2026, 7, 10)],
            "USD",
            PriceAdjustment::TotalReturnAdjusted,
        ),
    ];

    let report = align_holdings_prices(&holdings, &candidates, &policy()).expect("alignment");

    assert_eq!(report.covered().len(), 2);
    assert!(report.uncovered_listed().is_empty());
    assert_eq!(report.covered()[0].holding().instrument_id(), &equity);
    assert_eq!(report.covered()[1].holding().instrument_id(), &etf);
    assert!((report.weights().covered_weight().value() - 1.0).abs() < f64::EPSILON);
    assert!(report.weights().total_uncovered_weight().value().abs() < f64::EPSILON);
}

#[test]
fn preserves_partial_coverage_without_renormalizing() {
    let covered = instrument("COVERED");
    let missing = instrument("MISSING");
    let holdings = vec![
        holding(&covered, AssetClass::Equity, 0.4),
        holding(&missing, AssetClass::Equity, 0.5),
    ];
    let candidates = vec![candidate(
        &covered,
        &[date(2026, 7, 9), date(2026, 7, 10)],
        "USD",
        PriceAdjustment::TotalReturnAdjusted,
    )];

    let report = align_holdings_prices(&holdings, &candidates, &policy()).expect("alignment");

    assert_eq!(
        report.uncovered_listed()[0].reason(),
        &CoverageGapReason::MissingPriceSeries
    );
    assert!((report.weights().covered_weight().value() - 0.4).abs() < f64::EPSILON);
    assert!((report.weights().uncovered_listed_weight().value() - 0.5).abs() < f64::EPSILON);
    assert!((report.weights().unrepresented_weight().value() - 0.1).abs() < 1e-12);
}

#[test]
fn accepts_staleness_at_the_inclusive_boundary() {
    let id = instrument("EQUITY");
    let holdings = vec![holding(&id, AssetClass::Equity, 1.0)];
    let candidates = vec![candidate(
        &id,
        &[date(2026, 7, 6), date(2026, 7, 7)],
        "USD",
        PriceAdjustment::TotalReturnAdjusted,
    )];

    let report = align_holdings_prices(&holdings, &candidates, &policy()).expect("alignment");

    assert_eq!(report.covered().len(), 1);
}

#[test]
fn ignores_unused_candidate_contents() {
    let held = instrument("HELD");
    let unused = instrument("UNUSED");
    let holdings = vec![holding(&held, AssetClass::Equity, 1.0)];
    let candidates = vec![
        candidate(
            &held,
            &[date(2026, 7, 9), date(2026, 7, 10)],
            "USD",
            PriceAdjustment::TotalReturnAdjusted,
        ),
        candidate(
            &unused,
            &[date(2026, 7, 11), date(2026, 7, 12)],
            "USD",
            PriceAdjustment::TotalReturnAdjusted,
        ),
    ];

    let report = align_holdings_prices(&holdings, &candidates, &policy()).expect("alignment");

    assert_eq!(report.covered().len(), 1);
}
