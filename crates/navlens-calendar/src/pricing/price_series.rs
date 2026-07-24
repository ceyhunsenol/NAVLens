use super::calculation::{calculate_dated_decimal_returns, calculate_period_decimal_returns};
use super::validation::validate_date_sequence;
use crate::{DatedDecimalReturn, PeriodDecimalReturn, PriceObservation, PricingError};
use navlens_core::FundId;

/// A validated chronological unit-price series for one fund.
#[derive(Clone, Debug, PartialEq)]
pub struct PriceSeries {
    fund_id: FundId,
    observations: Vec<PriceObservation>,
}

impl PriceSeries {
    /// Creates a series containing at least two strictly increasing dates.
    ///
    /// # Errors
    /// Returns an error for too few observations, duplicate dates, or
    /// decreasing dates.
    pub fn new(fund_id: FundId, observations: Vec<PriceObservation>) -> Result<Self, PricingError> {
        validate_date_sequence(observations.iter().map(|obs| obs.date()))?;
        Ok(Self {
            fund_id,
            observations,
        })
    }

    #[must_use]
    pub const fn fund_id(&self) -> &FundId {
        &self.fund_id
    }

    #[must_use]
    pub fn observations(&self) -> &[PriceObservation] {
        &self.observations
    }

    /// Calculates one decimal return for every adjacent price pair.
    ///
    /// # Errors
    /// Returns an error if a finite price ratio produces a non-finite return.
    pub fn decimal_returns(&self) -> Result<Vec<DatedDecimalReturn>, PricingError> {
        calculate_dated_decimal_returns(&self.observations, |obs| (obs.date(), obs.unit_price()))
    }

    /// Calculates one period return for every adjacent price pair.
    ///
    /// # Errors
    /// Returns an error if a finite price ratio produces a non-finite return.
    pub fn period_returns(&self) -> Result<Vec<PeriodDecimalReturn>, PricingError> {
        calculate_period_decimal_returns(&self.observations, |obs| (obs.date(), obs.unit_price()))
    }
}
