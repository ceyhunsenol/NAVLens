use navlens_application::{AlignmentPolicy, SecurityPriceHistoryCandidate};
use navlens_calendar::{MarketDate, PriceAdjustment, SecurityPriceObservation};
use navlens_core::{
    AssetClass, CurrencyCode, HoldingPosition, InstrumentId, PortfolioWeight, UnitPrice,
};

pub fn date(year: i32, month: u8, day: u8) -> MarketDate {
    MarketDate::new(year, month, day).expect("valid date")
}

pub fn instrument(name: &str) -> InstrumentId {
    InstrumentId::new(name).expect("valid instrument")
}

pub fn currency(code: &str) -> CurrencyCode {
    CurrencyCode::new(code).expect("valid currency")
}

pub fn holding(id: &InstrumentId, asset_class: AssetClass, value: f64) -> HoldingPosition {
    HoldingPosition::new(
        id.clone(),
        asset_class,
        PortfolioWeight::new(value).expect("valid weight"),
    )
}

pub fn observation(
    market_date: MarketDate,
    id: &InstrumentId,
    currency: &CurrencyCode,
    adjustment: PriceAdjustment,
) -> SecurityPriceObservation {
    SecurityPriceObservation::new(
        id.clone(),
        market_date,
        UnitPrice::new(10.0).expect("valid price"),
        currency.clone(),
        adjustment,
    )
}

pub fn candidate(
    id: &InstrumentId,
    dates: &[MarketDate],
    currency_code: &str,
    adjustment: PriceAdjustment,
) -> SecurityPriceHistoryCandidate {
    let currency = currency(currency_code);
    let observations = dates
        .iter()
        .map(|date| observation(*date, id, &currency, adjustment))
        .collect();
    SecurityPriceHistoryCandidate::new(id.clone(), observations).expect("valid candidate")
}

pub fn policy() -> AlignmentPolicy {
    AlignmentPolicy::new(
        currency("USD"),
        PriceAdjustment::TotalReturnAdjusted,
        date(2026, 7, 10),
        2,
        3,
    )
    .expect("valid policy")
}
