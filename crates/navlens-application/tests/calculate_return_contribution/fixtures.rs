use navlens_application::{
    AlignmentPolicy, PortfolioCoverageReport, SecurityPriceHistoryCandidate, align_holdings_prices,
};
use navlens_calendar::{MarketDate, PriceAdjustment, SecurityPriceObservation};
use navlens_core::{
    AssetClass, CurrencyCode, HoldingPosition, InstrumentId, PortfolioWeight, UnitPrice,
};

pub(crate) fn date(year: i32, month: u8, day: u8) -> MarketDate {
    MarketDate::new(year, month, day).expect("test date should be valid")
}

pub(crate) fn holding(instrument_id: &str, weight: f64) -> HoldingPosition {
    HoldingPosition::new(
        InstrumentId::new(instrument_id).expect("test instrument ID should be valid"),
        AssetClass::Equity,
        PortfolioWeight::new(weight).expect("test weight should be valid"),
    )
}

pub(crate) fn candidate(
    instrument_id: &str,
    prices: &[(MarketDate, f64)],
) -> SecurityPriceHistoryCandidate {
    let instrument_id =
        InstrumentId::new(instrument_id).expect("test instrument ID should be valid");
    let observations = prices
        .iter()
        .map(|(market_date, price)| {
            SecurityPriceObservation::new(
                instrument_id.clone(),
                *market_date,
                UnitPrice::new(*price).expect("test price should be valid"),
                currency(),
                PriceAdjustment::TotalReturnAdjusted,
            )
        })
        .collect();

    SecurityPriceHistoryCandidate::new(instrument_id, observations)
        .expect("test candidate should be valid")
}

pub(crate) fn align(
    holdings: &[HoldingPosition],
    candidates: &[SecurityPriceHistoryCandidate],
    as_of_date: MarketDate,
) -> PortfolioCoverageReport {
    let policy = AlignmentPolicy::new(
        currency(),
        PriceAdjustment::TotalReturnAdjusted,
        as_of_date,
        2,
        5,
    )
    .expect("test policy should be valid");

    align_holdings_prices(holdings, candidates, &policy)
        .expect("test holdings and prices should align")
}

pub(crate) fn assert_approximately_equal(actual: f64, expected: f64) {
    const TEST_TOLERANCE: f64 = 1e-12;
    assert!(
        (actual - expected).abs() <= TEST_TOLERANCE,
        "expected {expected}, got {actual}"
    );
}

fn currency() -> CurrencyCode {
    CurrencyCode::new("USD").expect("test currency should be valid")
}
