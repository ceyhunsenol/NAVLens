use navlens_calendar::{FxRateObservation, FxRateSeries, MarketDate};
use navlens_core::{CurrencyCode, CurrencyPair, FxRate, FxRateKind};

fn usd_try() -> CurrencyPair {
    CurrencyPair::new(
        CurrencyCode::new("USD").unwrap(),
        CurrencyCode::new("TRY").unwrap(),
    )
    .unwrap()
}

fn make_obs(year: i32, month: u8, day: u8, rate_val: f64) -> FxRateObservation {
    FxRateObservation::new(
        usd_try(),
        MarketDate::new(year, month, day).unwrap(),
        FxRate::new(rate_val).unwrap(),
        FxRateKind::NonCashBuying,
    )
}

#[test]
fn returns_none_when_date_is_before_first_observation() {
    let obs1 = make_obs(2026, 1, 10, 35.0);
    let obs2 = make_obs(2026, 1, 15, 35.5);
    let series = FxRateSeries::new(vec![obs1, obs2]).unwrap();

    let before_date = MarketDate::new(2026, 1, 9).unwrap();
    assert_eq!(series.latest_observation_on_or_before(before_date), None);
}

#[test]
fn returns_exact_first_observation() {
    let obs1 = make_obs(2026, 1, 10, 35.0);
    let obs2 = make_obs(2026, 1, 15, 35.5);
    let series = FxRateSeries::new(vec![obs1.clone(), obs2]).unwrap();

    let first_date = MarketDate::new(2026, 1, 10).unwrap();
    let found = series
        .latest_observation_on_or_before(first_date)
        .expect("should find observation");
    assert_eq!(found, &obs1);
}

#[test]
fn returns_exact_middle_observation() {
    let obs1 = make_obs(2026, 1, 10, 35.0);
    let obs2 = make_obs(2026, 1, 15, 35.5);
    let obs3 = make_obs(2026, 1, 20, 36.0);
    let series = FxRateSeries::new(vec![obs1, obs2.clone(), obs3]).unwrap();

    let middle_date = MarketDate::new(2026, 1, 15).unwrap();
    let found = series
        .latest_observation_on_or_before(middle_date)
        .expect("should find observation");
    assert_eq!(found, &obs2);
}

#[test]
fn returns_previous_observation_when_date_is_between_observations() {
    let obs1 = make_obs(2026, 1, 10, 35.0);
    let obs2 = make_obs(2026, 1, 15, 35.5);
    let obs3 = make_obs(2026, 1, 20, 36.0);
    let series = FxRateSeries::new(vec![obs1, obs2.clone(), obs3]).unwrap();

    let between_date = MarketDate::new(2026, 1, 18).unwrap();
    let found = series
        .latest_observation_on_or_before(between_date)
        .expect("should find observation");
    assert_eq!(found, &obs2);
}

#[test]
fn returns_exact_final_observation() {
    let obs1 = make_obs(2026, 1, 10, 35.0);
    let obs2 = make_obs(2026, 1, 15, 35.5);
    let series = FxRateSeries::new(vec![obs1, obs2.clone()]).unwrap();

    let final_date = MarketDate::new(2026, 1, 15).unwrap();
    let found = series
        .latest_observation_on_or_before(final_date)
        .expect("should find observation");
    assert_eq!(found, &obs2);
}

#[test]
fn returns_final_observation_when_date_is_after_final_observation() {
    let obs1 = make_obs(2026, 1, 10, 35.0);
    let obs2 = make_obs(2026, 1, 15, 35.5);
    let series = FxRateSeries::new(vec![obs1, obs2.clone()]).unwrap();

    let after_date = MarketDate::new(2026, 1, 25).unwrap();
    let found = series
        .latest_observation_on_or_before(after_date)
        .expect("should find observation");
    assert_eq!(found, &obs2);
}

#[test]
fn handles_singleton_series_before_exact_after() {
    let obs = make_obs(2026, 1, 15, 35.25);
    let series = FxRateSeries::new(vec![obs.clone()]).unwrap();

    let before = MarketDate::new(2026, 1, 14).unwrap();
    let exact = MarketDate::new(2026, 1, 15).unwrap();
    let after = MarketDate::new(2026, 1, 16).unwrap();

    assert_eq!(series.latest_observation_on_or_before(before), None);
    assert_eq!(series.latest_observation_on_or_before(exact), Some(&obs));
    assert_eq!(series.latest_observation_on_or_before(after), Some(&obs));
}

#[test]
fn returned_observation_preserves_typed_pair_kind_rate_and_market_date() {
    let pair = usd_try();
    let date = MarketDate::new(2026, 1, 15).unwrap();
    let rate = FxRate::new(35.25).unwrap();
    let kind = FxRateKind::NonCashBuying;
    let obs = FxRateObservation::new(pair.clone(), date, rate, kind);

    let series = FxRateSeries::new(vec![obs]).unwrap();

    let found = series
        .latest_observation_on_or_before(date)
        .expect("should find observation");

    assert_eq!(found.pair(), &pair);
    assert_eq!(found.market_date(), date);
    assert_eq!(found.rate(), rate);
    assert_eq!(found.kind(), kind);
}
