use crate::{MarketDate, PricingError};

/// A validated observation period spanning two distinct, chronologically ordered market dates.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct ReturnPeriod {
    period_start_date: MarketDate,
    period_end_date: MarketDate,
}

impl ReturnPeriod {
    /// Creates a new `ReturnPeriod` after validating that `period_start_date` is strictly before `period_end_date`.
    ///
    /// # Errors
    /// Returns `PricingError::InvalidReturnPeriod` if `period_start_date` is on or after `period_end_date`.
    pub fn new(
        period_start_date: MarketDate,
        period_end_date: MarketDate,
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
        })
    }

    /// Returns the start date of the period.
    #[must_use]
    pub const fn period_start_date(self) -> MarketDate {
        self.period_start_date
    }

    /// Returns the end date of the period.
    #[must_use]
    pub const fn period_end_date(self) -> MarketDate {
        self.period_end_date
    }
}
