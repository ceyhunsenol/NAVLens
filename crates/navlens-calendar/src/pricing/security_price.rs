use crate::MarketDate;
use navlens_core::{CurrencyCode, InstrumentId, UnitPrice};

/// Corporate-action adjustment policy applied to a security price.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum PriceAdjustment {
    /// Raw unadjusted price as traded on the exchange.
    Unadjusted,
    /// Price adjusted for stock splits and share consolidations.
    SplitAdjusted,
    /// Price adjusted for both stock splits and cash dividend distributions.
    TotalReturnAdjusted,
}

/// A validated monetary end-of-day price observation for a specific security.
#[derive(Clone, Debug, PartialEq)]
pub struct SecurityPriceObservation {
    instrument_id: InstrumentId,
    market_date: MarketDate,
    price: UnitPrice,
    currency: CurrencyCode,
    adjustment: PriceAdjustment,
}

impl SecurityPriceObservation {
    /// Creates a new security price observation.
    #[must_use]
    pub const fn new(
        instrument_id: InstrumentId,
        market_date: MarketDate,
        price: UnitPrice,
        currency: CurrencyCode,
        adjustment: PriceAdjustment,
    ) -> Self {
        Self {
            instrument_id,
            market_date,
            price,
            currency,
            adjustment,
        }
    }

    /// Returns the instrument identifier.
    #[must_use]
    pub const fn instrument_id(&self) -> &InstrumentId {
        &self.instrument_id
    }

    /// Returns the market date.
    #[must_use]
    pub const fn market_date(&self) -> MarketDate {
        self.market_date
    }

    /// Returns the unit price.
    #[must_use]
    pub const fn price(&self) -> UnitPrice {
        self.price
    }

    /// Returns the currency code.
    #[must_use]
    pub const fn currency(&self) -> &CurrencyCode {
        &self.currency
    }

    /// Returns the price adjustment policy.
    #[must_use]
    pub const fn adjustment(&self) -> PriceAdjustment {
        self.adjustment
    }
}
