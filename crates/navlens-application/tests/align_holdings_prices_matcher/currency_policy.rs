use super::fixtures::{candidate, date, holding, instrument, policy};
use navlens_application::{CoverageGapReason, PriceCurrencyPolicy, align_holdings_prices};
use navlens_calendar::PriceAdjustment;
use navlens_core::AssetClass;

#[test]
fn default_policy_is_fund_base_only_and_reports_currency_mismatch() {
    let inst = instrument("EUR_SEC");
    let h = holding(&inst, AssetClass::Equity, 0.5);
    let c = candidate(
        &inst,
        &[date(2026, 7, 9), date(2026, 7, 10)],
        "EUR",
        PriceAdjustment::TotalReturnAdjusted,
    );

    let pol = policy();
    assert_eq!(
        pol.price_currency_policy(),
        PriceCurrencyPolicy::FundBaseOnly
    );

    let report = align_holdings_prices(&[h], &[c], &pol).unwrap();
    assert_eq!(report.uncovered_listed().len(), 1);
    assert!(matches!(
        report.uncovered_listed()[0].reason(),
        CoverageGapReason::CurrencyMismatch { .. }
    ));
}

#[test]
fn permit_foreign_covers_valid_foreign_series() {
    let inst = instrument("EUR_SEC");
    let h = holding(&inst, AssetClass::Equity, 0.5);
    let c = candidate(
        &inst,
        &[date(2026, 7, 9), date(2026, 7, 10)],
        "EUR",
        PriceAdjustment::TotalReturnAdjusted,
    );

    let pol = policy().with_price_currency_policy(PriceCurrencyPolicy::PermitForeign);
    let report = align_holdings_prices(&[h], &[c], &pol).unwrap();

    assert!(report.uncovered_listed().is_empty());
    assert!((report.weights().covered_weight().value() - 0.5).abs() < f64::EPSILON);
}

#[test]
fn permit_foreign_does_not_bypass_incompatible_price_adjustment() {
    let inst = instrument("EUR_SEC");
    let h = holding(&inst, AssetClass::Equity, 0.5);
    let c = candidate(
        &inst,
        &[date(2026, 7, 9), date(2026, 7, 10)],
        "EUR",
        PriceAdjustment::Unadjusted,
    );

    let pol = policy().with_price_currency_policy(PriceCurrencyPolicy::PermitForeign);
    let report = align_holdings_prices(&[h], &[c], &pol).unwrap();

    assert_eq!(report.uncovered_listed().len(), 1);
    assert!(matches!(
        report.uncovered_listed()[0].reason(),
        CoverageGapReason::IncompatiblePriceAdjustment { .. }
    ));
}

#[test]
fn permit_foreign_does_not_bypass_stale_price_detection() {
    let inst = instrument("EUR_SEC");
    let h = holding(&inst, AssetClass::Equity, 0.5);
    let c = candidate(
        &inst,
        &[date(2026, 7, 1), date(2026, 7, 2)],
        "EUR",
        PriceAdjustment::TotalReturnAdjusted,
    );

    let pol = policy().with_price_currency_policy(PriceCurrencyPolicy::PermitForeign);
    let report = align_holdings_prices(&[h], &[c], &pol).unwrap();

    assert_eq!(report.uncovered_listed().len(), 1);
    assert!(matches!(
        report.uncovered_listed()[0].reason(),
        CoverageGapReason::StalePrices { .. }
    ));
}

#[test]
fn same_currency_behavior_is_identical_under_both_policies() {
    let inst = instrument("USD_SEC");
    let h = holding(&inst, AssetClass::Equity, 0.5);
    let c = candidate(
        &inst,
        &[date(2026, 7, 9), date(2026, 7, 10)],
        "USD",
        PriceAdjustment::TotalReturnAdjusted,
    );

    let pol1 = policy();
    let pol2 = policy().with_price_currency_policy(PriceCurrencyPolicy::PermitForeign);

    let r1 =
        align_holdings_prices(std::slice::from_ref(&h), std::slice::from_ref(&c), &pol1).unwrap();
    let r2 =
        align_holdings_prices(std::slice::from_ref(&h), std::slice::from_ref(&c), &pol2).unwrap();

    assert!(r1.uncovered_listed().is_empty());
    assert!(r2.uncovered_listed().is_empty());
    assert!(
        (r1.weights().covered_weight().value() - r2.weights().covered_weight().value()).abs()
            < f64::EPSILON
    );
}

#[test]
fn portfolio_coverage_report_preserves_configured_policy() {
    let inst = instrument("USD_SEC");
    let h = holding(&inst, AssetClass::Equity, 0.5);
    let c = candidate(
        &inst,
        &[date(2026, 7, 9), date(2026, 7, 10)],
        "USD",
        PriceAdjustment::TotalReturnAdjusted,
    );

    let pol = policy().with_price_currency_policy(PriceCurrencyPolicy::PermitForeign);
    let report = align_holdings_prices(&[h], &[c], &pol).unwrap();

    assert_eq!(report.policy(), &pol);
    assert_eq!(
        report.policy().price_currency_policy(),
        PriceCurrencyPolicy::PermitForeign
    );
}
