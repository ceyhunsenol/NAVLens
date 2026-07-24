use navlens_calendar::{MarketDate, PriceObservation, PriceSeries, PricingError};
use navlens_core::{FundId, UnitPrice};

fn date(day: u8) -> MarketDate {
    MarketDate::new(2026, 1, day).expect("valid test date")
}

fn observation(day: u8, price: f64) -> PriceObservation {
    PriceObservation::new(date(day), UnitPrice::new(price).expect("valid test price"))
}

fn fund_id() -> FundId {
    FundId::new("ABC").expect("valid test fund")
}

fn shared_fixture() -> Vec<PriceObservation> {
    include_str!("fixtures/prices.csv")
        .lines()
        .skip(1)
        .map(|line| {
            let (date_text, price_text) = line.split_once(',').expect("fixture row");
            let mut parts = date_text
                .split('-')
                .map(|part| part.parse::<i32>().expect("numeric date component"));
            let year = parts.next().expect("fixture year");
            let month = u8::try_from(parts.next().expect("fixture month")).expect("month");
            let day = u8::try_from(parts.next().expect("fixture day")).expect("day");
            PriceObservation::new(
                MarketDate::new(year, month, day).expect("valid fixture date"),
                UnitPrice::new(price_text.parse().expect("numeric fixture price"))
                    .expect("valid fixture price"),
            )
        })
        .collect()
}

#[test]
fn calculates_returns_with_the_current_price_date() {
    let series = PriceSeries::new(
        fund_id(),
        vec![
            observation(2, 100.0),
            observation(5, 101.0),
            observation(6, 100.495),
        ],
    )
    .expect("valid price series");

    let returns = series.decimal_returns().expect("finite returns");

    assert_eq!(returns.len(), 2);
    assert_eq!(returns[0].date(), date(5));
    assert!((returns[0].decimal_return().value() - 0.01).abs() < 1e-12);
    assert_eq!(returns[1].date(), date(6));
    assert!((returns[1].decimal_return().value() + 0.005).abs() < 1e-12);
}

#[test]
fn calculates_period_returns_with_exact_dates() {
    let series = PriceSeries::new(
        fund_id(),
        vec![
            observation(2, 100.0),
            observation(5, 101.0),
            observation(6, 100.495),
        ],
    )
    .expect("valid price series");

    let decimal_returns = series.decimal_returns().expect("finite returns");
    let period_returns = series.period_returns().expect("finite period returns");

    assert_eq!(period_returns.len(), 2);

    assert_eq!(period_returns[0].period_start_date(), date(2));
    assert_eq!(period_returns[0].period_end_date(), date(5));
    assert_eq!(
        period_returns[0].decimal_return(),
        decimal_returns[0].decimal_return()
    );

    assert_eq!(period_returns[1].period_start_date(), date(5));
    assert_eq!(period_returns[1].period_end_date(), date(6));
    assert_eq!(
        period_returns[1].decimal_return(),
        decimal_returns[1].decimal_return()
    );
}

#[test]
fn rejects_short_duplicate_and_decreasing_series() {
    assert_eq!(
        PriceSeries::new(fund_id(), vec![observation(2, 100.0)]),
        Err(PricingError::InsufficientPriceObservations(1))
    );
    assert_eq!(
        PriceSeries::new(
            fund_id(),
            vec![observation(2, 100.0), observation(2, 101.0)]
        ),
        Err(PricingError::DuplicatePriceDate(date(2)))
    );
    assert_eq!(
        PriceSeries::new(
            fund_id(),
            vec![observation(5, 100.0), observation(2, 101.0)]
        ),
        Err(PricingError::NonChronologicalPriceDate {
            previous: date(5),
            current: date(2),
        })
    );
}

#[test]
fn shared_fixture_has_expected_decimal_returns() {
    let series = PriceSeries::new(fund_id(), shared_fixture()).expect("valid fixture series");
    let actual: Vec<_> = series
        .decimal_returns()
        .expect("finite fixture returns")
        .into_iter()
        .map(|value| value.decimal_return().value())
        .collect();

    let expected = [0.01, -0.005, 0.015, -0.002, 0.01];
    for (actual, expected) in actual.iter().zip(expected) {
        assert!((actual - expected).abs() < 1e-12);
    }
}
