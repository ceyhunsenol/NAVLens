use crate::MarketDate;
use navlens_core::DecimalReturn;

/// A decimal return ending on a specific published-price date.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct DatedDecimalReturn {
    date: MarketDate,
    decimal_return: DecimalReturn,
}

impl DatedDecimalReturn {
    #[must_use]
    pub const fn new(date: MarketDate, decimal_return: DecimalReturn) -> Self {
        Self {
            date,
            decimal_return,
        }
    }

    #[must_use]
    pub const fn date(self) -> MarketDate {
        self.date
    }

    #[must_use]
    pub const fn decimal_return(self) -> DecimalReturn {
        self.decimal_return
    }
}
