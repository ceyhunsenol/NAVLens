use super::calculation::{calculate_dated_decimal_returns, calculate_period_decimal_returns};
use super::validation::validate_date_sequence;
use crate::{
    DatedDecimalReturn, PeriodDecimalReturn, PriceAdjustment, PricingError,
    SecurityPriceObservation,
};
use navlens_core::{CurrencyCode, InstrumentId};

/// A validated, homogeneous, chronological series of security price observations.
#[derive(Clone, Debug, PartialEq)]
pub struct SecurityPriceSeries {
    observations: Vec<SecurityPriceObservation>,
}

impl SecurityPriceSeries {
    /// Creates a new series containing at least two strictly increasing dates.
    ///
    /// # Errors
    /// Returns a pricing error if there are fewer than two observations, if there are duplicate or
    /// non-chronological dates, or if the observations are not homogeneous (different instrument,
    /// currency, or adjustment).
    pub fn new(observations: Vec<SecurityPriceObservation>) -> Result<Self, PricingError> {
        validate_date_sequence(
            observations
                .iter()
                .map(SecurityPriceObservation::market_date),
        )?;
        validate_series_identity(&observations)?;
        Ok(Self { observations })
    }

    /// Returns the shared instrument identifier of the series.
    #[must_use]
    pub fn instrument_id(&self) -> &InstrumentId {
        self.observations[0].instrument_id()
    }

    /// Returns the shared currency code of the series.
    #[must_use]
    pub fn currency(&self) -> &CurrencyCode {
        self.observations[0].currency()
    }

    /// Returns the shared price adjustment policy of the series.
    #[must_use]
    pub fn adjustment(&self) -> PriceAdjustment {
        self.observations[0].adjustment()
    }

    /// Returns a reference to the sequence of observations.
    #[must_use]
    pub fn observations(&self) -> &[SecurityPriceObservation] {
        &self.observations
    }

    /// Calculates one decimal return for every adjacent price pair.
    ///
    /// # Errors
    /// Returns an error if a finite price ratio produces a non-finite return.
    pub fn decimal_returns(&self) -> Result<Vec<DatedDecimalReturn>, PricingError> {
        calculate_dated_decimal_returns(&self.observations, |obs| (obs.market_date(), obs.price()))
    }

    /// Calculates one period decimal return for every adjacent price pair.
    ///
    /// # Errors
    /// Returns an error if a finite price ratio produces a non-finite return or if period dates are invalid.
    pub fn period_returns(&self) -> Result<Vec<PeriodDecimalReturn>, PricingError> {
        calculate_period_decimal_returns(&self.observations, |obs| (obs.market_date(), obs.price()))
    }
}

fn validate_series_identity(observations: &[SecurityPriceObservation]) -> Result<(), PricingError> {
    let first = &observations[0];
    let expected_inst = first.instrument_id();
    let expected_curr = first.currency();
    let expected_adj = first.adjustment();

    for obs in &observations[1..] {
        if obs.instrument_id() != expected_inst {
            return Err(PricingError::MixedInstrumentId {
                expected: expected_inst.clone(),
                found: obs.instrument_id().clone(),
            });
        }
        if obs.currency() != expected_curr {
            return Err(PricingError::MixedCurrencyCode {
                expected: expected_curr.clone(),
                found: obs.currency().clone(),
            });
        }
        if obs.adjustment() != expected_adj {
            return Err(PricingError::MixedPriceAdjustment {
                expected: expected_adj,
                found: obs.adjustment(),
            });
        }
    }
    Ok(())
}
