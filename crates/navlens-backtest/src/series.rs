use crate::{BacktestError, Observation};
use navlens_core::FundId;

/// A validated chronological sequence of observations for one fund.
#[derive(Clone, Debug, PartialEq)]
pub struct BacktestSeries {
    fund_id: FundId,
    observations: Vec<Observation>,
}

impl BacktestSeries {
    /// Creates a non-empty, chronologically ordered series for one fund.
    ///
    /// # Errors
    /// Returns an error for an empty series, duplicate target date, decreasing
    /// target date, or decreasing prediction date.
    pub fn new(fund_id: FundId, observations: Vec<Observation>) -> Result<Self, BacktestError> {
        if observations.is_empty() {
            return Err(BacktestError::NoObservations);
        }

        for pair in observations.windows(2) {
            let previous = pair[0];
            let current = pair[1];

            if current.target_date() == previous.target_date() {
                return Err(BacktestError::DuplicateTargetDate(current.target_date()));
            }
            if current.target_date() < previous.target_date() {
                return Err(BacktestError::NonChronologicalTargetDate {
                    previous: previous.target_date(),
                    current: current.target_date(),
                });
            }
            if current.prediction_date() < previous.prediction_date() {
                return Err(BacktestError::NonChronologicalPredictionDate {
                    previous: previous.prediction_date(),
                    current: current.prediction_date(),
                });
            }
        }

        validate_confidence_levels(&observations)?;

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
    pub fn observations(&self) -> &[Observation] {
        &self.observations
    }
}

fn validate_confidence_levels(observations: &[Observation]) -> Result<(), BacktestError> {
    let mut expected = None;

    for observation in observations {
        let Some(interval) = observation.prediction_interval() else {
            continue;
        };
        let confidence = interval.confidence_level();

        match expected {
            Some(level) if level != confidence => {
                return Err(BacktestError::MixedConfidenceLevels {
                    expected: level,
                    actual: confidence,
                });
            }
            None => expected = Some(confidence),
            Some(_) => {}
        }
    }

    Ok(())
}
