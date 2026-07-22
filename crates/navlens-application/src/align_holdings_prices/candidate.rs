use crate::align_holdings_prices::error::AlignmentContractError;
use navlens_calendar::SecurityPriceObservation;
use navlens_core::InstrumentId;

/// A candidate history of security prices for alignment.
#[derive(Clone, Debug, PartialEq)]
pub struct SecurityPriceHistoryCandidate {
    instrument_id: InstrumentId,
    observations: Vec<SecurityPriceObservation>,
}

impl SecurityPriceHistoryCandidate {
    /// Creates a new `SecurityPriceHistoryCandidate`.
    ///
    /// # Errors
    /// Returns an error if the candidate is empty or if any observation's
    /// `instrument_id` does not match the candidate's `instrument_id`.
    pub fn new(
        instrument_id: InstrumentId,
        observations: Vec<SecurityPriceObservation>,
    ) -> Result<Self, AlignmentContractError> {
        if observations.is_empty() {
            return Err(AlignmentContractError::EmptyHistoryCandidate { instrument_id });
        }

        for observation in &observations {
            if observation.instrument_id() != &instrument_id {
                return Err(AlignmentContractError::CandidateInstrumentMismatch {
                    expected: instrument_id,
                    found: observation.instrument_id().clone(),
                });
            }
        }

        Ok(Self {
            instrument_id,
            observations,
        })
    }

    /// Returns the candidate's instrument ID.
    #[must_use]
    pub fn instrument_id(&self) -> &InstrumentId {
        &self.instrument_id
    }

    /// Returns the candidate's price observations.
    #[must_use]
    pub fn observations(&self) -> &[SecurityPriceObservation] {
        &self.observations
    }
}
