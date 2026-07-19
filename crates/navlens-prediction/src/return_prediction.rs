use crate::{ModelDescriptor, PredictionError};
use navlens_core::{DecimalReturn, PredictionInterval};

/// A point estimate, its uncertainty interval, and reproducibility metadata.
#[derive(Clone, Debug, PartialEq)]
pub struct ReturnPrediction {
    expected_return: DecimalReturn,
    interval: PredictionInterval,
    model: ModelDescriptor,
}

impl ReturnPrediction {
    /// Creates a validated return prediction.
    ///
    /// # Errors
    /// Returns [`PredictionError`] when the point estimate falls outside its
    /// uncertainty interval.
    pub fn new(
        expected_return: DecimalReturn,
        interval: PredictionInterval,
        model: ModelDescriptor,
    ) -> Result<Self, PredictionError> {
        if !interval.contains(expected_return) {
            return Err(PredictionError::ExpectedReturnOutsideInterval {
                expected: expected_return.value(),
                lower: interval.lower().value(),
                upper: interval.upper().value(),
            });
        }

        Ok(Self {
            expected_return,
            interval,
            model,
        })
    }

    #[must_use]
    pub const fn expected_return(&self) -> DecimalReturn {
        self.expected_return
    }

    #[must_use]
    pub const fn interval(&self) -> PredictionInterval {
        self.interval
    }

    #[must_use]
    pub const fn model(&self) -> &ModelDescriptor {
        &self.model
    }
}
