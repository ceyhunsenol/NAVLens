use crate::align_holdings_prices::error::AlignmentContractError;
use navlens_calendar::{MarketDate, PriceAdjustment};
use navlens_core::CurrencyCode;

/// Defines the policy for aligning security prices to holdings.
#[derive(Clone, Debug, PartialEq)]
pub struct AlignmentPolicy {
    fund_base_currency: CurrencyCode,
    required_price_adjustment: PriceAdjustment,
    pricing_as_of_date: MarketDate,
    minimum_observations: usize,
    max_staleness_calendar_days: u32,
}

impl AlignmentPolicy {
    /// Creates a new `AlignmentPolicy`.
    ///
    /// # Errors
    /// Returns an error if `minimum_observations` is less than 2.
    pub fn new(
        fund_base_currency: CurrencyCode,
        required_price_adjustment: PriceAdjustment,
        pricing_as_of_date: MarketDate,
        minimum_observations: usize,
        max_staleness_calendar_days: u32,
    ) -> Result<Self, AlignmentContractError> {
        if minimum_observations < 2 {
            return Err(AlignmentContractError::InvalidMinimumObservations {
                found: minimum_observations,
            });
        }

        Ok(Self {
            fund_base_currency,
            required_price_adjustment,
            pricing_as_of_date,
            minimum_observations,
            max_staleness_calendar_days,
        })
    }

    /// Returns the fund's base currency.
    #[must_use]
    pub fn fund_base_currency(&self) -> &CurrencyCode {
        &self.fund_base_currency
    }

    /// Returns the required price adjustment.
    #[must_use]
    pub const fn required_price_adjustment(&self) -> PriceAdjustment {
        self.required_price_adjustment
    }

    /// Returns the pricing as-of date.
    #[must_use]
    pub const fn pricing_as_of_date(&self) -> MarketDate {
        self.pricing_as_of_date
    }

    /// Returns the minimum number of observations required.
    #[must_use]
    pub fn minimum_observations(&self) -> usize {
        self.minimum_observations
    }

    /// Returns the maximum allowed staleness in calendar days.
    #[must_use]
    pub fn max_staleness_calendar_days(&self) -> u32 {
        self.max_staleness_calendar_days
    }
}
