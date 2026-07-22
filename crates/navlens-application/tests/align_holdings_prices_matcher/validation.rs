use super::fixtures::{candidate, currency, date, holding, instrument, observation, policy};
use navlens_application::{
    AlignHoldingsPricesError, SecurityPriceHistoryCandidate, align_holdings_prices,
};
use navlens_calendar::{PriceAdjustment, PricingError};
use navlens_core::{AssetClass, CoreError};

#[test]
fn rejects_duplicate_holding() {
    let id = instrument("EQUITY");
    let holdings = vec![
        holding(&id, AssetClass::Equity, 0.5),
        holding(&id, AssetClass::Equity, 0.5),
    ];

    assert_eq!(
        align_holdings_prices(&holdings, &[], &policy()),
        Err(AlignHoldingsPricesError::DuplicateHoldingInstrument(id))
    );
}

#[test]
fn rejects_duplicate_candidate() {
    let id = instrument("EQUITY");
    let holdings = vec![holding(&id, AssetClass::Equity, 1.0)];
    let first = candidate(
        &id,
        &[date(2026, 7, 9), date(2026, 7, 10)],
        "USD",
        PriceAdjustment::TotalReturnAdjusted,
    );

    assert_eq!(
        align_holdings_prices(&holdings, &[first.clone(), first], &policy()),
        Err(AlignHoldingsPricesError::DuplicateHistoryCandidate(id))
    );
}

#[test]
fn future_observation_is_fatal_before_insufficient_gap() {
    let id = instrument("EQUITY");
    let future = date(2026, 7, 11);
    let holdings = vec![holding(&id, AssetClass::Equity, 1.0)];
    let candidates = vec![candidate(
        &id,
        &[future],
        "USD",
        PriceAdjustment::TotalReturnAdjusted,
    )];

    assert_eq!(
        align_holdings_prices(&holdings, &candidates, &policy()),
        Err(AlignHoldingsPricesError::ObservationAfterPricingAsOf {
            instrument_id: id,
            observation_date: future,
            pricing_as_of_date: date(2026, 7, 10),
        })
    );
}

#[test]
fn rejects_non_chronological_history() {
    let id = instrument("EQUITY");
    let holdings = vec![holding(&id, AssetClass::Equity, 1.0)];
    let candidates = vec![candidate(
        &id,
        &[date(2026, 7, 9), date(2026, 7, 8)],
        "USD",
        PriceAdjustment::TotalReturnAdjusted,
    )];

    assert_eq!(
        align_holdings_prices(&holdings, &candidates, &policy()),
        Err(AlignHoldingsPricesError::InvalidPriceHistory {
            instrument_id: id,
            source: PricingError::NonChronologicalPriceDate {
                previous: date(2026, 7, 9),
                current: date(2026, 7, 8),
            },
        })
    );
}

#[test]
fn rejects_mixed_currency_history_as_invalid() {
    let id = instrument("EQUITY");
    let usd = currency("USD");
    let eur = currency("EUR");
    let observations = vec![
        observation(
            date(2026, 7, 9),
            &id,
            &usd,
            PriceAdjustment::TotalReturnAdjusted,
        ),
        observation(
            date(2026, 7, 10),
            &id,
            &eur,
            PriceAdjustment::TotalReturnAdjusted,
        ),
    ];
    let candidate = SecurityPriceHistoryCandidate::new(id.clone(), observations)
        .expect("candidate identity is valid");
    let holdings = vec![holding(&id, AssetClass::Equity, 1.0)];

    let error = align_holdings_prices(&holdings, &[candidate], &policy()).expect_err("invalid");

    assert!(matches!(
        error,
        AlignHoldingsPricesError::InvalidPriceHistory {
            source: PricingError::MixedCurrencyCode { .. },
            ..
        }
    ));
}

#[test]
fn delegates_excess_declared_weight_to_core_coverage_arithmetic() {
    let first = instrument("FIRST");
    let second = instrument("SECOND");
    let holdings = vec![
        holding(&first, AssetClass::Equity, 0.7),
        holding(&second, AssetClass::Equity, 0.6),
    ];

    let error = align_holdings_prices(&holdings, &[], &policy()).expect_err("invalid weights");

    match error {
        AlignHoldingsPricesError::CoverageArithmetic {
            source: CoreError::DeclaredWeightExceedsFundTotal(total),
        } => assert!((total - 1.3).abs() < 1e-12),
        other => panic!("unexpected error: {other}"),
    }
}
