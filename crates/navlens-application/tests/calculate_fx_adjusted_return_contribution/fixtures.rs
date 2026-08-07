use navlens_application::{
    AlignmentPolicy, PortfolioCoverageReport, PriceCurrencyPolicy, SecurityPriceHistoryCandidate,
    align_holdings_prices,
};
use navlens_calendar::{
    FxRateObservation, FxRateSeries, MarketDate, PriceAdjustment, ReturnPeriod,
    SecurityPriceObservation,
};
use navlens_core::{
    AssetClass, CurrencyCode, CurrencyPair, FxRate, FxRateKind, HoldingPosition, InstrumentId,
    PortfolioWeight, UnitPrice,
};

pub(crate) fn date(year: i32, month: u8, day: u8) -> MarketDate {
    MarketDate::new(year, month, day).expect("test date should be valid")
}

pub(crate) fn period(start: MarketDate, end: MarketDate) -> ReturnPeriod {
    ReturnPeriod::new(start, end).expect("test return period should be valid")
}

pub(crate) fn currency(code: &str) -> CurrencyCode {
    CurrencyCode::new(code).expect("test currency should be valid")
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
    curr: &str,
    prices: &[(MarketDate, f64)],
) -> SecurityPriceHistoryCandidate {
    let instrument_id =
        InstrumentId::new(instrument_id).expect("test instrument ID should be valid");
    let c = currency(curr);
    let observations = prices
        .iter()
        .map(|(market_date, price)| {
            SecurityPriceObservation::new(
                instrument_id.clone(),
                *market_date,
                UnitPrice::new(*price).expect("test price should be valid"),
                c.clone(),
                PriceAdjustment::TotalReturnAdjusted,
            )
        })
        .collect();

    SecurityPriceHistoryCandidate::new(instrument_id, observations)
        .expect("test candidate should be valid")
}

pub(crate) fn fx_series(
    base: &str,
    quote: &str,
    kind: FxRateKind,
    points: &[(MarketDate, f64)],
) -> FxRateSeries {
    let pair = CurrencyPair::new(currency(base), currency(quote)).expect("pair should be valid");
    let observations = points
        .iter()
        .map(|(market_date, rate)| {
            FxRateObservation::new(
                pair.clone(),
                *market_date,
                FxRate::new(*rate).expect("test rate should be valid"),
                kind,
            )
        })
        .collect();

    FxRateSeries::new(observations).expect("test series should be valid")
}

pub(crate) fn align(
    holdings: &[HoldingPosition],
    candidates: &[SecurityPriceHistoryCandidate],
    as_of_date: MarketDate,
    base_curr: &str,
    price_policy: PriceCurrencyPolicy,
) -> PortfolioCoverageReport {
    let policy = AlignmentPolicy::new(
        currency(base_curr),
        PriceAdjustment::TotalReturnAdjusted,
        as_of_date,
        2,
        5,
    )
    .expect("test policy should be valid")
    .with_price_currency_policy(price_policy);

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
