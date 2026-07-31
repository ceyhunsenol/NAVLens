use navlens_calendar::{
    FxRateObservation, FxRateSeries, MarketDate, PriceAdjustment, PriceObservation, PriceSeries,
    PricingError, SecurityPriceObservation, SecurityPriceSeries,
};
use navlens_core::{CurrencyCode, CurrencyPair, FxRate, FxRateKind, InstrumentId, UnitPrice};

fn usd_try() -> CurrencyPair {
    CurrencyPair::new(
        CurrencyCode::new("USD").unwrap(),
        CurrencyCode::new("TRY").unwrap(),
    )
    .unwrap()
}

fn eur_try() -> CurrencyPair {
    CurrencyPair::new(
        CurrencyCode::new("EUR").unwrap(),
        CurrencyCode::new("TRY").unwrap(),
    )
    .unwrap()
}

fn make_obs(date: MarketDate, rate_val: f64) -> FxRateObservation {
    FxRateObservation::new(
        usd_try(),
        date,
        FxRate::new(rate_val).unwrap(),
        FxRateKind::NonCashBuying,
    )
}

#[test]
fn fx_rate_observation_preserves_all_typed_fields() {
    let pair = usd_try();
    let date = MarketDate::new(2026, 1, 15).unwrap();
    let rate = FxRate::new(35.25).unwrap();
    let kind = FxRateKind::NonCashBuying;

    let obs = FxRateObservation::new(pair.clone(), date, rate, kind);

    assert_eq!(obs.pair(), &pair);
    assert_eq!(obs.market_date(), date);
    assert_eq!(obs.rate(), rate);
    assert_eq!(obs.kind(), kind);
}

#[test]
fn accepts_single_observation_series() {
    let obs = make_obs(MarketDate::new(2026, 1, 15).unwrap(), 35.25);
    let series =
        FxRateSeries::new(vec![obs.clone()]).expect("single observation series should be valid");

    assert_eq!(series.pair(), &usd_try());
    assert_eq!(series.kind(), FxRateKind::NonCashBuying);
    assert_eq!(series.observations(), &[obs]);
}

#[test]
fn accepts_multiple_chronological_observations_and_varying_rates() {
    let obs1 = make_obs(MarketDate::new(2026, 1, 15).unwrap(), 35.25);
    let obs2 = make_obs(MarketDate::new(2026, 1, 16).unwrap(), 35.50);
    let obs3 = make_obs(MarketDate::new(2026, 1, 17).unwrap(), 35.10);

    let series = FxRateSeries::new(vec![obs1.clone(), obs2.clone(), obs3.clone()])
        .expect("chronological series should be valid");

    assert_eq!(series.pair(), &usd_try());
    assert_eq!(series.kind(), FxRateKind::NonCashBuying);
    assert_eq!(series.observations(), &[obs1, obs2, obs3]);
}

#[test]
fn rejects_empty_fx_rate_series() {
    let result = FxRateSeries::new(vec![]);
    assert_eq!(result, Err(PricingError::EmptyFxRateSeries));
}

#[test]
fn rejects_duplicate_fx_rate_date() {
    let d = MarketDate::new(2026, 1, 15).unwrap();
    let obs1 = make_obs(d, 35.25);
    let obs2 = make_obs(d, 35.30);

    let result = FxRateSeries::new(vec![obs1, obs2]);
    assert_eq!(result, Err(PricingError::DuplicateFxRateDate(d)));
}

#[test]
fn rejects_non_chronological_fx_rate_date() {
    let d1 = MarketDate::new(2026, 1, 16).unwrap();
    let d2 = MarketDate::new(2026, 1, 15).unwrap();
    let obs1 = make_obs(d1, 35.25);
    let obs2 = make_obs(d2, 35.30);

    let result = FxRateSeries::new(vec![obs1, obs2]);
    assert_eq!(
        result,
        Err(PricingError::NonChronologicalFxRateDate {
            previous: d1,
            current: d2,
        })
    );
}

#[test]
fn rejects_mixed_currency_pair() {
    let d1 = MarketDate::new(2026, 1, 15).unwrap();
    let d2 = MarketDate::new(2026, 1, 16).unwrap();

    let obs1 = FxRateObservation::new(
        usd_try(),
        d1,
        FxRate::new(35.25).unwrap(),
        FxRateKind::NonCashBuying,
    );
    let obs2 = FxRateObservation::new(
        eur_try(),
        d2,
        FxRate::new(38.10).unwrap(),
        FxRateKind::NonCashBuying,
    );

    let result = FxRateSeries::new(vec![obs1, obs2]);
    assert_eq!(
        result,
        Err(PricingError::MixedCurrencyPair {
            expected: usd_try(),
            found: eur_try(),
        })
    );
}

#[test]
fn rejects_mixed_fx_rate_kind() {
    let d1 = MarketDate::new(2026, 1, 15).unwrap();
    let d2 = MarketDate::new(2026, 1, 16).unwrap();

    let obs1 = FxRateObservation::new(
        usd_try(),
        d1,
        FxRate::new(35.25).unwrap(),
        FxRateKind::NonCashBuying,
    );
    let obs2 = FxRateObservation::new(
        usd_try(),
        d2,
        FxRate::new(35.30).unwrap(),
        FxRateKind::CashBuying,
    );

    let result = FxRateSeries::new(vec![obs1, obs2]);
    assert_eq!(
        result,
        Err(PricingError::MixedFxRateKind {
            expected: FxRateKind::NonCashBuying,
            found: FxRateKind::CashBuying,
        })
    );
}

#[test]
fn preserves_existing_price_series_and_security_price_series_behavior() {
    let fund_id = navlens_core::FundId::new("ABC").unwrap();
    let inst_id = InstrumentId::new("INST1").unwrap();
    let usd = CurrencyCode::new("USD").unwrap();
    let d1 = MarketDate::new(2026, 1, 15).unwrap();
    let d2 = MarketDate::new(2026, 1, 16).unwrap();

    // Empty and single observation rejected for PriceSeries and SecurityPriceSeries
    let p_obs1 = PriceObservation::new(d1, UnitPrice::new(10.0).unwrap());
    assert_eq!(
        PriceSeries::new(fund_id.clone(), vec![]),
        Err(PricingError::InsufficientPriceObservations(0))
    );
    assert_eq!(
        PriceSeries::new(fund_id.clone(), vec![p_obs1]),
        Err(PricingError::InsufficientPriceObservations(1))
    );

    let s_obs1 = SecurityPriceObservation::new(
        inst_id.clone(),
        d1,
        UnitPrice::new(10.0).unwrap(),
        usd.clone(),
        PriceAdjustment::Unadjusted,
    );
    assert_eq!(
        SecurityPriceSeries::new(vec![]),
        Err(PricingError::InsufficientPriceObservations(0))
    );
    assert_eq!(
        SecurityPriceSeries::new(vec![s_obs1.clone()]),
        Err(PricingError::InsufficientPriceObservations(1))
    );

    // Duplicate dates produce DuplicatePriceDate
    let p_obs2 = PriceObservation::new(d1, UnitPrice::new(11.0).unwrap());
    assert_eq!(
        PriceSeries::new(fund_id, vec![p_obs1, p_obs2]),
        Err(PricingError::DuplicatePriceDate(d1))
    );

    let s_obs2 = SecurityPriceObservation::new(
        inst_id,
        d1,
        UnitPrice::new(11.0).unwrap(),
        usd,
        PriceAdjustment::Unadjusted,
    );
    assert_eq!(
        SecurityPriceSeries::new(vec![s_obs1, s_obs2]),
        Err(PricingError::DuplicatePriceDate(d1))
    );

    // Decreasing dates produce NonChronologicalPriceDate
    let p_obs_dec1 = PriceObservation::new(d2, UnitPrice::new(10.0).unwrap());
    let p_obs_dec2 = PriceObservation::new(d1, UnitPrice::new(11.0).unwrap());
    assert_eq!(
        PriceSeries::new(
            navlens_core::FundId::new("XYZ").unwrap(),
            vec![p_obs_dec1, p_obs_dec2]
        ),
        Err(PricingError::NonChronologicalPriceDate {
            previous: d2,
            current: d1,
        })
    );
}
