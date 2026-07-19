use crate::{DatedDecimalReturn, PriceObservation, PricingError};
use navlens_core::{FundId, calculate_decimal_return};

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
        validate_observations(&observations)?;
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
        self.observations
            .windows(2)
            .map(|pair| {
                let current = pair[1];
                calculate_decimal_return(pair[0].unit_price(), current.unit_price())
                    .map(|value| DatedDecimalReturn::new(current.date(), value))
                    .map_err(PricingError::ReturnCalculation)
            })
            .collect()
    }
}

fn validate_observations(observations: &[PriceObservation]) -> Result<(), PricingError> {
    if observations.len() < 2 {
        return Err(PricingError::InsufficientPriceObservations(
            observations.len(),
        ));
    }
    for pair in observations.windows(2) {
        let previous = pair[0].date();
        let current = pair[1].date();
        if current == previous {
            return Err(PricingError::DuplicatePriceDate(current));
        }
        if current < previous {
            return Err(PricingError::NonChronologicalPriceDate { previous, current });
        }
    }
    Ok(())
}
