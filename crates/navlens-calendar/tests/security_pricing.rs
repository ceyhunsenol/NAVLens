use navlens_calendar::{MarketDate, PriceAdjustment, SecurityPriceObservation};
use navlens_core::{CurrencyCode, InstrumentId, UnitPrice};

fn date(year: i32, month: u8, day: u8) -> MarketDate {
    MarketDate::new(year, month, day).expect("valid date")
}

fn instrument_id(id: &str) -> InstrumentId {
    InstrumentId::new(id).expect("valid instrument")
}

fn price(value: f64) -> UnitPrice {
    UnitPrice::new(value).expect("valid price")
}

fn currency(code: &str) -> CurrencyCode {
    CurrencyCode::new(code).expect("valid currency")
}

#[test]
fn preserves_all_fields_and_supports_adjustment_variants() {
    let inst = instrument_id("US67066G1040");
    let mdate = date(2026, 1, 31);
    let uprice = price(100.0);
    let curr = currency("USD");

    let adjustments = [
        PriceAdjustment::Unadjusted,
        PriceAdjustment::SplitAdjusted,
        PriceAdjustment::TotalReturnAdjusted,
    ];

    for adj in adjustments {
        let obs = SecurityPriceObservation::new(inst.clone(), mdate, uprice, curr.clone(), adj);

        assert_eq!(obs.instrument_id(), &inst);
        assert_eq!(obs.market_date(), mdate);
        assert_eq!(obs.price(), uprice);
        assert_eq!(obs.currency(), &curr);
        assert_eq!(obs.adjustment(), adj);
    }
}

#[test]
fn enforces_explicit_instrument_and_currency_distinctions() {
    let inst_a = instrument_id("US67066G1040");
    let inst_b = instrument_id("US5949181045");
    let mdate = date(2026, 1, 31);
    let uprice = price(100.0);
    let curr_usd = currency("USD");
    let curr_try = currency("TRY");

    let obs_a = SecurityPriceObservation::new(
        inst_a.clone(),
        mdate,
        uprice,
        curr_usd.clone(),
        PriceAdjustment::Unadjusted,
    );

    let obs_b = SecurityPriceObservation::new(
        inst_b.clone(),
        mdate,
        uprice,
        curr_try.clone(),
        PriceAdjustment::Unadjusted,
    );

    assert_ne!(obs_a, obs_b);
}
