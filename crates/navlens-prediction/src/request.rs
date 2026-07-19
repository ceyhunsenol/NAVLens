use crate::{PredictionError, UtcTimestamp};
use navlens_calendar::MarketDate;
use navlens_core::FundId;

/// The identity, horizon, and data cut-off for one prediction operation.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PredictionRequest {
    fund_id: FundId,
    prediction_date: MarketDate,
    target_date: MarketDate,
    generated_at: UtcTimestamp,
    data_as_of: UtcTimestamp,
}

impl PredictionRequest {
    /// Creates a prediction request with an explicit market date and UTC audit
    /// timestamps.
    ///
    /// # Errors
    /// Returns [`PredictionError`] when the target is not after the prediction
    /// date or when the data cut-off is later than generation time.
    pub fn new(
        fund_id: FundId,
        prediction_date: MarketDate,
        target_date: MarketDate,
        generated_at: UtcTimestamp,
        data_as_of: UtcTimestamp,
    ) -> Result<Self, PredictionError> {
        if prediction_date >= target_date {
            return Err(PredictionError::PredictionNotBeforeTarget {
                prediction: prediction_date,
                target: target_date,
            });
        }
        if data_as_of > generated_at {
            return Err(PredictionError::DataAfterGeneration {
                data_as_of_unix_seconds: data_as_of.unix_seconds(),
                generated_at_unix_seconds: generated_at.unix_seconds(),
            });
        }

        Ok(Self {
            fund_id,
            prediction_date,
            target_date,
            generated_at,
            data_as_of,
        })
    }

    #[must_use]
    pub const fn fund_id(&self) -> &FundId {
        &self.fund_id
    }

    #[must_use]
    pub const fn prediction_date(&self) -> MarketDate {
        self.prediction_date
    }

    #[must_use]
    pub const fn target_date(&self) -> MarketDate {
        self.target_date
    }

    #[must_use]
    pub const fn generated_at(&self) -> UtcTimestamp {
        self.generated_at
    }

    #[must_use]
    pub const fn data_as_of(&self) -> UtcTimestamp {
        self.data_as_of
    }
}
