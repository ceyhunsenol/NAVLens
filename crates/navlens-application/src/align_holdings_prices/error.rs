use navlens_core::InstrumentId;
use std::error::Error;
use std::fmt::{Display, Formatter};

/// Errors that can occur when building alignment contracts.
#[derive(Clone, Debug, PartialEq)]
pub enum AlignmentContractError {
    /// The minimum observations required is less than 2.
    InvalidMinimumObservations {
        /// Invalid requested minimum.
        found: usize,
    },
    /// The price history candidate is empty.
    EmptyHistoryCandidate {
        /// Instrument whose candidate contains no observations.
        instrument_id: InstrumentId,
    },
    /// An observation's instrument ID does not match the candidate's instrument ID.
    CandidateInstrumentMismatch {
        /// Instrument expected by the candidate.
        expected: InstrumentId,
        /// Instrument found on the observation.
        found: InstrumentId,
    },
}

impl Display for AlignmentContractError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidMinimumObservations { found } => write!(
                formatter,
                "minimum observations must be at least 2; got {found}"
            ),
            Self::EmptyHistoryCandidate { instrument_id } => write!(
                formatter,
                "price history candidate for '{instrument_id}' cannot be empty"
            ),
            Self::CandidateInstrumentMismatch { expected, found } => write!(
                formatter,
                "candidate instrument ID '{expected}' does not match observation instrument ID '{found}'"
            ),
        }
    }
}

impl Error for AlignmentContractError {}
