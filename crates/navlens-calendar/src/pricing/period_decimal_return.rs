use crate::{MarketDate, PricingError};
use navlens_core::DecimalReturn;

/// A decimal return computed over a specific market observation period.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PeriodDecimalReturn {
    period_start_date: MarketDate,
    period_end_date: MarketDate,
    decimal_return: DecimalReturn,
}

impl PeriodDecimalReturn {
    /// Creates a new `PeriodDecimalReturn` after validating that `period_start_date` is strictly before `period_end_date`.
    ///
    /// # Errors
    /// Returns `PricingError::InvalidReturnPeriod` if `period_start_date` is on or after `period_end_date`.
    pub fn new(
        period_start_date: MarketDate,
        period_end_date: MarketDate,
        decimal_return: DecimalReturn,
    ) -> Result<Self, PricingError> {
        if period_start_date >= period_end_date {
            return Err(PricingError::InvalidReturnPeriod {
                period_start_date,
                period_end_date,
            });
        }
        Ok(Self {
            period_start_date,
            period_end_date,
            decimal_return,
        })
    }

    /// Returns the start date of the return period.
    #[must_use]
    pub const fn period_start_date(self) -> MarketDate {
        self.period_start_date
    }

    /// Returns the end date of the return period.
    #[must_use]
    pub const fn period_end_date(self) -> MarketDate {
        self.period_end_date
    }

    /// Returns the calculated decimal return.
    #[must_use]
    pub const fn decimal_return(self) -> DecimalReturn {
        self.decimal_return
    }
}
