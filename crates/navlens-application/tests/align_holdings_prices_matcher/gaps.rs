use super::fixtures::{candidate, date, holding, instrument, policy};
use navlens_application::{CoverageGapReason, align_holdings_prices};
use navlens_calendar::PriceAdjustment;
use navlens_core::AssetClass;

#[test]
fn applies_deterministic_gap_precedence() {
    let unsupported = instrument("UNSUPPORTED");
    let missing = instrument("MISSING");
    let insufficient = instrument("INSUFFICIENT");
    let currency = instrument("CURRENCY");
    let adjustment = instrument("ADJUSTMENT");
    let stale = instrument("STALE");
    let holdings = vec![
        holding(&unsupported, AssetClass::DebtSecurity, 0.1),
        holding(&missing, AssetClass::Equity, 0.1),
        holding(&insufficient, AssetClass::Equity, 0.1),
        holding(&currency, AssetClass::Equity, 0.1),
        holding(&adjustment, AssetClass::Equity, 0.1),
        holding(&stale, AssetClass::Equity, 0.1),
    ];
    let candidates = vec![
        candidate(
            &unsupported,
            &[date(2026, 7, 11), date(2026, 7, 12)],
            "EUR",
            PriceAdjustment::Unadjusted,
        ),
        candidate(
            &insufficient,
            &[date(2026, 7, 5)],
            "EUR",
            PriceAdjustment::Unadjusted,
        ),
        candidate(
            &currency,
            &[date(2026, 7, 5), date(2026, 7, 6)],
            "EUR",
            PriceAdjustment::Unadjusted,
        ),
        candidate(
            &adjustment,
            &[date(2026, 7, 5), date(2026, 7, 6)],
            "USD",
            PriceAdjustment::Unadjusted,
        ),
        candidate(
            &stale,
            &[date(2026, 7, 5), date(2026, 7, 6)],
            "USD",
            PriceAdjustment::TotalReturnAdjusted,
        ),
    ];

    let report = align_holdings_prices(&holdings, &candidates, &policy()).expect("alignment");
    let reasons: Vec<_> = report
        .uncovered_listed()
        .iter()
        .map(navlens_application::UncoveredHolding::reason)
        .collect();

    assert_eq!(
        reasons[0],
        &CoverageGapReason::UnsupportedAssetClass {
            asset_class: AssetClass::DebtSecurity
        }
    );
    assert_eq!(reasons[1], &CoverageGapReason::MissingPriceSeries);
    assert_eq!(
        reasons[2],
        &CoverageGapReason::InsufficientObservations {
            found: 1,
            required: 2
        }
    );
    assert!(matches!(
        reasons[3],
        CoverageGapReason::CurrencyMismatch { .. }
    ));
    assert!(matches!(
        reasons[4],
        CoverageGapReason::IncompatiblePriceAdjustment { .. }
    ));
    assert!(matches!(reasons[5], CoverageGapReason::StalePrices { .. }));
}
