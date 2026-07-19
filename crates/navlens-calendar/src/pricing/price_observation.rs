use crate::MarketDate;
use navlens_core::UnitPrice;

/// A validated unit price published for one market date.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PriceObservation {
    date: MarketDate,
    unit_price: UnitPrice,
}

impl PriceObservation {
    #[must_use]
    pub const fn new(date: MarketDate, unit_price: UnitPrice) -> Self {
        Self { date, unit_price }
    }

    #[must_use]
    pub const fn date(self) -> MarketDate {
        self.date
    }

    #[must_use]
    pub const fn unit_price(self) -> UnitPrice {
        self.unit_price
    }
}
