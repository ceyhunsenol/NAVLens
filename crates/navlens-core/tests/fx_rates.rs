use navlens_core::{CoreError, CurrencyCode, CurrencyPair, FxRate, FxRateKind};
use std::collections::HashSet;

#[test]
fn creates_distinct_currency_pair_and_preserves_direction() {
    let usd = CurrencyCode::new("USD").unwrap();
    let try_code = CurrencyCode::new("TRY").unwrap();
    let pair = CurrencyPair::new(usd.clone(), try_code.clone()).unwrap();

    assert_eq!(pair.base_currency(), &usd);
    assert_eq!(pair.quote_currency(), &try_code);
}

#[test]
fn rejects_identical_currency_pair() {
    let usd = CurrencyCode::new("USD").unwrap();
    let result = CurrencyPair::new(usd.clone(), usd);

    assert_eq!(result, Err(CoreError::IdenticalCurrencyPair));
}

#[test]
fn verifies_currency_pair_equality_ordering_and_hash() {
    let usd = CurrencyCode::new("USD").unwrap();
    let try_code = CurrencyCode::new("TRY").unwrap();
    let eur = CurrencyCode::new("EUR").unwrap();

    let usd_try = CurrencyPair::new(usd.clone(), try_code.clone()).unwrap();
    let usd_try_dup = CurrencyPair::new(usd.clone(), try_code.clone()).unwrap();
    let eur_try = CurrencyPair::new(eur, try_code).unwrap();
    let try_usd = CurrencyPair::new(CurrencyCode::new("TRY").unwrap(), usd).unwrap();

    assert_eq!(usd_try, usd_try_dup);
    assert_ne!(usd_try, try_usd);

    assert!(eur_try < usd_try);

    let mut set = HashSet::new();
    assert!(set.insert(usd_try.clone()));
    assert!(!set.insert(usd_try_dup));
    assert!(set.contains(&usd_try));
}

#[test]
fn accepts_positive_finite_fx_rate_and_preserves_exact_scalar() {
    let rate_val = 35.25;
    let rate = FxRate::new(rate_val).unwrap();

    assert!((rate.quote_currency_per_one_base_currency() - rate_val).abs() < f64::EPSILON);
}

#[test]
fn rejects_zero_and_negative_fx_rates() {
    assert_eq!(FxRate::new(0.0), Err(CoreError::FxRateNotPositive(0.0)));
    assert_eq!(FxRate::new(-12.5), Err(CoreError::FxRateNotPositive(-12.5)));
}

#[test]
fn rejects_non_finite_fx_rates() {
    assert_eq!(FxRate::new(f64::NAN), Err(CoreError::NonFiniteNumber));
    assert_eq!(FxRate::new(f64::INFINITY), Err(CoreError::NonFiniteNumber));
    assert_eq!(
        FxRate::new(f64::NEG_INFINITY),
        Err(CoreError::NonFiniteNumber)
    );
}

#[test]
fn verifies_fx_rate_kind_variants_distinctness_and_hash() {
    let kinds = [
        FxRateKind::NonCashBuying,
        FxRateKind::NonCashSelling,
        FxRateKind::CashBuying,
        FxRateKind::CashSelling,
    ];

    let mut set = HashSet::new();
    for kind in kinds {
        assert!(set.insert(kind));
    }

    assert_eq!(set.len(), 4);
    assert_ne!(FxRateKind::NonCashBuying, FxRateKind::NonCashSelling);
    assert_ne!(FxRateKind::CashBuying, FxRateKind::CashSelling);
}
