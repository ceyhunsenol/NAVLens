use navlens_calendar::{MarketDate, PricingError};
use navlens_core::{CoreError, InstrumentId};
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

/// Fatal errors that invalidate an alignment request.
#[derive(Clone, Debug, PartialEq)]
pub enum AlignHoldingsPricesError {
    /// The holdings snapshot contains duplicate entries for the same instrument.
    DuplicateHoldingInstrument(InstrumentId),
    /// The candidates list contains duplicate entries for the same instrument.
    DuplicateHistoryCandidate(InstrumentId),
    /// An observation exists after the pricing as-of date.
    ObservationAfterPricingAsOf {
        /// Instrument whose history contains the future observation.
        instrument_id: InstrumentId,
        /// Observation date that exceeds the policy boundary.
        observation_date: MarketDate,
        /// Inclusive upper date bound from the alignment policy.
        pricing_as_of_date: MarketDate,
    },
    /// A candidate price history fails chronological or homogeneity validation.
    InvalidPriceHistory {
        /// The instrument identifier of the invalid history.
        instrument_id: InstrumentId,
        /// The underlying pricing error.
        source: PricingError,
    },
    /// An error occurred during coverage weight arithmetic.
    CoverageArithmetic {
        /// The underlying core error.
        source: CoreError,
    },
}

impl Display for AlignHoldingsPricesError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::DuplicateHoldingInstrument(instrument_id) => {
                write!(formatter, "duplicate holding instrument: {instrument_id}")
            }
            Self::DuplicateHistoryCandidate(instrument_id) => {
                write!(formatter, "duplicate history candidate: {instrument_id}")
            }
            Self::ObservationAfterPricingAsOf {
                instrument_id,
                observation_date,
                pricing_as_of_date,
            } => write!(
                formatter,
                "observation for {instrument_id} dated {observation_date} is after pricing as-of date {pricing_as_of_date}"
            ),
            Self::InvalidPriceHistory {
                instrument_id,
                source,
            } => {
                write!(
                    formatter,
                    "invalid price history for {instrument_id}: {source}"
                )
            }
            Self::CoverageArithmetic { source } => {
                write!(formatter, "coverage arithmetic error: {source}")
            }
        }
    }
}

impl Error for AlignHoldingsPricesError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::InvalidPriceHistory { source, .. } => Some(source),
            Self::CoverageArithmetic { source } => Some(source),
            _ => None,
        }
    }
}
