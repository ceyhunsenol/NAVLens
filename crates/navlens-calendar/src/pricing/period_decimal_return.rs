use crate::{MarketDate, PricingError, ReturnPeriod};
use navlens_core::DecimalReturn;

/// A decimal return computed over a specific market observation period.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PeriodDecimalReturn {
    period: ReturnPeriod,
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
        let period = ReturnPeriod::new(period_start_date, period_end_date)?;
        Ok(Self {
            period,
            decimal_return,
        })
    }

    /// Creates a new `PeriodDecimalReturn` from a validated `ReturnPeriod`.
    #[must_use]
    pub const fn from_period(period: ReturnPeriod, decimal_return: DecimalReturn) -> Self {
        Self {
            period,
            decimal_return,
        }
    }

    /// Returns the observation period of the return.
    #[must_use]
    pub const fn period(self) -> ReturnPeriod {
        self.period
    }

    /// Returns the start date of the return period.
    #[must_use]
    pub const fn period_start_date(self) -> MarketDate {
        self.period.period_start_date()
    }

    /// Returns the end date of the return period.
    #[must_use]
    pub const fn period_end_date(self) -> MarketDate {
        self.period.period_end_date()
    }

    /// Returns the calculated decimal return.
    #[must_use]
    pub const fn decimal_return(self) -> DecimalReturn {
        self.decimal_return
    }
}
