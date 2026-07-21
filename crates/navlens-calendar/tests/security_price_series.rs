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
