use crate::BacktestError;
use navlens_calendar::MarketDate;
use navlens_core::DecimalReturn;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Observation {
    prediction_date: MarketDate,
    target_date: MarketDate,
    predicted_return: DecimalReturn,
    actual_return: DecimalReturn,
}

impl Observation {
    /// Creates a dated prediction observation.
    ///
    /// # Errors
    /// Returns [`BacktestError::PredictionNotBeforeTarget`] unless the
    /// prediction date is strictly earlier than the target date.
    pub fn new(
        prediction_date: MarketDate,
        target_date: MarketDate,
        predicted_return: DecimalReturn,
        actual_return: DecimalReturn,
    ) -> Result<Self, BacktestError> {
        if prediction_date >= target_date {
            return Err(BacktestError::PredictionNotBeforeTarget {
                prediction: prediction_date,
                target: target_date,
            });
        }

        Ok(Self {
            prediction_date,
            target_date,
            predicted_return,
            actual_return,
        })
    }

    #[must_use]
    pub const fn prediction_date(self) -> MarketDate {
        self.prediction_date
    }

    #[must_use]
    pub const fn target_date(self) -> MarketDate {
        self.target_date
    }

    #[must_use]
    pub const fn predicted_return(self) -> DecimalReturn {
        self.predicted_return
    }

    #[must_use]
    pub const fn actual_return(self) -> DecimalReturn {
        self.actual_return
    }
}
