use navlens_calendar::{
    MarketDate, PriceAdjustment, PricingError, SecurityPriceObservation, SecurityPriceSeries,
};
use navlens_core::{CurrencyCode, InstrumentId, UnitPrice};

fn date(day: u8) -> MarketDate {
    MarketDate::new(2026, 1, day).expect("valid date")
}

fn instrument_id(value: &str) -> InstrumentId {
    InstrumentId::new(value).expect("valid instrument")
}

fn currency(value: &str) -> CurrencyCode {
    CurrencyCode::new(value).expect("valid currency")
}

fn observation(
    instrument: &str,
    day: u8,
    currency_code: &str,
    adjustment: PriceAdjustment,
) -> SecurityPriceObservation {
    SecurityPriceObservation::new(
        instrument_id(instrument),
        date(day),
        UnitPrice::new(100.0).expect("valid price"),
        currency(currency_code),
        adjustment,
    )
}

#[test]
fn creates_homogeneous_series() {
    let first = observation("AAPL", 1, "USD", PriceAdjustment::Unadjusted);
    let second = observation("AAPL", 2, "USD", PriceAdjustment::Unadjusted);
    let third = observation("AAPL", 3, "USD", PriceAdjustment::Unadjusted);

    let series = SecurityPriceSeries::new(vec![first.clone(), second.clone(), third.clone()])
        .expect("valid series");

    assert_eq!(series.instrument_id().as_str(), "AAPL");
    assert_eq!(series.currency().as_str(), "USD");
    assert_eq!(series.adjustment(), PriceAdjustment::Unadjusted);
    assert_eq!(series.observations(), &[first, second, third]);
}

#[test]
fn rejects_insufficient_observations() {
    let observation = observation("AAPL", 1, "USD", PriceAdjustment::Unadjusted);

    assert_eq!(
        SecurityPriceSeries::new(vec![observation]),
        Err(PricingError::InsufficientPriceObservations(1))
    );
}

#[test]
fn rejects_duplicate_dates() {
    let first = observation("AAPL", 1, "USD", PriceAdjustment::Unadjusted);
    let second = observation("AAPL", 1, "USD", PriceAdjustment::Unadjusted);

    assert_eq!(
        SecurityPriceSeries::new(vec![first, second]),
        Err(PricingError::DuplicatePriceDate(date(1)))
    );
}

#[test]
fn rejects_decreasing_dates() {
    let first = observation("AAPL", 2, "USD", PriceAdjustment::Unadjusted);
    let second = observation("AAPL", 1, "USD", PriceAdjustment::Unadjusted);

    assert_eq!(
        SecurityPriceSeries::new(vec![first, second]),
        Err(PricingError::NonChronologicalPriceDate {
            previous: date(2),
            current: date(1),
        })
    );
}

#[test]
fn rejects_mixed_instruments() {
    let first = observation("AAPL", 1, "USD", PriceAdjustment::Unadjusted);
    let second = observation("MSFT", 2, "USD", PriceAdjustment::Unadjusted);

    assert_eq!(
        SecurityPriceSeries::new(vec![first, second]),
        Err(PricingError::MixedInstrumentId {
            expected: instrument_id("AAPL"),
            found: instrument_id("MSFT"),
        })
    );
}

#[test]
fn rejects_mixed_currencies() {
    let first = observation("AAPL", 1, "USD", PriceAdjustment::Unadjusted);
    let second = observation("AAPL", 2, "EUR", PriceAdjustment::Unadjusted);

    assert_eq!(
        SecurityPriceSeries::new(vec![first, second]),
        Err(PricingError::MixedCurrencyCode {
            expected: currency("USD"),
            found: currency("EUR"),
        })
    );
}

#[test]
fn rejects_mixed_adjustments() {
    let first = observation("AAPL", 1, "USD", PriceAdjustment::Unadjusted);
    let second = observation("AAPL", 2, "USD", PriceAdjustment::SplitAdjusted);

    assert_eq!(
        SecurityPriceSeries::new(vec![first, second]),
        Err(PricingError::MixedPriceAdjustment {
            expected: PriceAdjustment::Unadjusted,
            found: PriceAdjustment::SplitAdjusted,
        })
    );
}

fn observation_with_price(
    instrument: &str,
    day: u8,
    price: f64,
    currency_code: &str,
    adjustment: PriceAdjustment,
) -> SecurityPriceObservation {
    SecurityPriceObservation::new(
        instrument_id(instrument),
        date(day),
        UnitPrice::new(price).expect("valid price"),
        currency(currency_code),
        adjustment,
    )
}

#[test]
fn calculates_decimal_returns_for_security_price_series() {
    let first = observation_with_price("AAPL", 2, 100.0, "USD", PriceAdjustment::Unadjusted);
    let second = observation_with_price("AAPL", 5, 101.0, "USD", PriceAdjustment::Unadjusted);
    let third = observation_with_price("AAPL", 6, 100.495, "USD", PriceAdjustment::Unadjusted);

    let series = SecurityPriceSeries::new(vec![first, second, third]).expect("valid series");
    let returns = series.decimal_returns().expect("finite returns");

    assert_eq!(returns.len(), 2);
    assert_eq!(returns[0].date(), date(5));
    assert!((returns[0].decimal_return().value() - 0.01).abs() < 1e-12);
    assert_eq!(returns[1].date(), date(6));
    assert!((returns[1].decimal_return().value() + 0.005).abs() < 1e-12);
}

#[test]
fn decimal_returns_parity_with_price_series() {
    use navlens_calendar::{PriceObservation, PriceSeries};
    use navlens_core::FundId;

    let fund_id = FundId::new("AAPL").expect("valid fund id");
    let dates_and_prices = [(2, 100.0), (5, 101.0), (6, 100.495), (10, 102.0)];

    let fund_observations: Vec<_> = dates_and_prices
        .iter()
        .map(|&(day, price)| {
            PriceObservation::new(date(day), UnitPrice::new(price).expect("valid price"))
        })
        .collect();
    let price_series = PriceSeries::new(fund_id, fund_observations).expect("valid price series");

    let security_observations: Vec<_> = dates_and_prices
        .iter()
        .map(|&(day, price)| {
            observation_with_price("AAPL", day, price, "USD", PriceAdjustment::Unadjusted)
        })
        .collect();
    let security_price_series =
        SecurityPriceSeries::new(security_observations).expect("valid security price series");

    let fund_returns = price_series.decimal_returns().expect("valid returns");
    let security_returns = security_price_series
        .decimal_returns()
        .expect("valid returns");

    assert_eq!(fund_returns, security_returns);
}
