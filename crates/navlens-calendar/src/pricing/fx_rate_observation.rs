use crate::MarketDate;
use navlens_core::{CurrencyPair, FxRate, FxRateKind};

/// A validated foreign exchange rate observation for a specific currency pair and market date.
#[derive(Clone, Debug, PartialEq)]
pub struct FxRateObservation {
    pair: CurrencyPair,
    market_date: MarketDate,
    rate: FxRate,
    kind: FxRateKind,
}

impl FxRateObservation {
    /// Creates a new foreign exchange rate observation.
    #[must_use]
    pub const fn new(
        pair: CurrencyPair,
        market_date: MarketDate,
        rate: FxRate,
        kind: FxRateKind,
    ) -> Self {
        Self {
            pair,
            market_date,
            rate,
            kind,
        }
    }

    /// Returns the currency pair of the observation.
    #[must_use]
    pub const fn pair(&self) -> &CurrencyPair {
        &self.pair
    }

    /// Returns the market date of the observation.
    #[must_use]
    pub const fn market_date(&self) -> MarketDate {
        self.market_date
    }

    /// Returns the rate value of the observation.
    #[must_use]
    pub const fn rate(&self) -> FxRate {
        self.rate
    }

    /// Returns the economic rate kind of the observation.
    #[must_use]
    pub const fn kind(&self) -> FxRateKind {
        self.kind
    }
}
