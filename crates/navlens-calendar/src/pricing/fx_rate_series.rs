use super::validation::{DateSequenceViolation, validate_strict_date_order};
use crate::{FxRateObservation, MarketDate, PricingError};
use navlens_core::{CurrencyPair, FxRateKind};

/// A validated, homogeneous, chronological series of foreign exchange rate observations.
#[derive(Clone, Debug, PartialEq)]
pub struct FxRateSeries {
    observations: Vec<FxRateObservation>,
}

impl FxRateSeries {
    /// Creates a new series containing at least one strictly increasing date observation.
    ///
    /// # Errors
    /// Returns a pricing error if there are no observations, if there are duplicate or
    /// non-chronological dates, or if the observations are not homogeneous (different currency pair or rate kind).
    pub fn new(observations: Vec<FxRateObservation>) -> Result<Self, PricingError> {
        match validate_strict_date_order(observations.iter().map(FxRateObservation::market_date)) {
            Ok(0) => return Err(PricingError::EmptyFxRateSeries),
            Ok(_) => {}
            Err(DateSequenceViolation::Duplicate(date)) => {
                return Err(PricingError::DuplicateFxRateDate(date));
            }
            Err(DateSequenceViolation::NonChronological { previous, current }) => {
                return Err(PricingError::NonChronologicalFxRateDate { previous, current });
            }
        }
        validate_series_identity(&observations)?;
        Ok(Self { observations })
    }

    /// Returns the shared currency pair of the series.
    #[must_use]
    pub fn pair(&self) -> &CurrencyPair {
        self.observations[0].pair()
    }

    /// Returns the shared rate kind of the series.
    #[must_use]
    pub fn kind(&self) -> FxRateKind {
        self.observations[0].kind()
    }

    /// Returns a reference to the sequence of observations.
    #[must_use]
    pub fn observations(&self) -> &[FxRateObservation] {
        &self.observations
    }

    /// Returns the latest observation on or before `date`.
    ///
    /// Returns `None` if `date` is before the first observation date in the series.
    #[must_use]
    pub fn latest_observation_on_or_before(&self, date: MarketDate) -> Option<&FxRateObservation> {
        let index = self
            .observations
            .partition_point(|obs| obs.market_date() <= date);
        if index == 0 {
            None
        } else {
            Some(&self.observations[index - 1])
        }
    }
}

fn validate_series_identity(observations: &[FxRateObservation]) -> Result<(), PricingError> {
    let first = &observations[0];
    let expected_pair = first.pair();
    let expected_kind = first.kind();

    for obs in &observations[1..] {
        if obs.pair() != expected_pair {
            return Err(PricingError::MixedCurrencyPair {
                expected: expected_pair.clone(),
                found: obs.pair().clone(),
            });
        }
        if obs.kind() != expected_kind {
            return Err(PricingError::MixedFxRateKind {
                expected: expected_kind,
                found: obs.kind(),
            });
        }
    }
    Ok(())
}
