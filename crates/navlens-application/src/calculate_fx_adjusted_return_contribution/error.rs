use navlens_calendar::MarketDate;
use navlens_core::{CoreError, CurrencyPair, DecimalReturn, FxRateKind};
use std::error::Error;
use std::fmt::{Display, Formatter};

/// Errors that can occur when constructing FX return evidence contracts.
#[derive(Clone, Debug, PartialEq)]
pub enum FxReturnContractError {
    /// The observation date is after the requested boundary date.
    ObservationAfterRequestedBoundary {
        /// Requested boundary date.
        requested_date: MarketDate,
        /// Observation market date.
        observation_date: MarketDate,
    },
    /// The declared staleness does not match the actual calendar-day difference.
    StalenessMismatch {
        /// Requested boundary date.
        requested_date: MarketDate,
        /// Observation market date.
        observation_date: MarketDate,
        /// Declared staleness in calendar days.
        declared: u32,
        /// Actual difference in calendar days.
        actual: i64,
    },
    /// The currency pairs of the start and end boundary evidence do not match.
    BoundaryCurrencyPairMismatch {
        /// Start boundary currency pair.
        start_pair: CurrencyPair,
        /// End boundary currency pair.
        end_pair: CurrencyPair,
    },
    /// The FX rate kinds of the start and end boundary evidence do not match.
    BoundaryFxRateKindMismatch {
        /// Start boundary FX rate kind.
        start_kind: FxRateKind,
        /// End boundary FX rate kind.
        end_kind: FxRateKind,
    },
    /// The supplied FX return does not match the canonical calculated return.
    FxReturnMismatch {
        /// Supplied decimal return.
        supplied: DecimalReturn,
        /// Canonical calculated decimal return.
        calculated: DecimalReturn,
    },
    /// A core domain error occurred during FX calculation.
    Core(CoreError),
}

impl Display for FxReturnContractError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ObservationAfterRequestedBoundary {
                requested_date,
                observation_date,
            } => write!(
                formatter,
                "observation date {observation_date} is after requested boundary date {requested_date}"
            ),
            Self::StalenessMismatch {
                requested_date,
                observation_date,
                declared,
                actual,
            } => write!(
                formatter,
                "declared staleness {declared} calendar days does not match actual difference of {actual} calendar days between observation date {observation_date} and requested boundary date {requested_date}"
            ),
            Self::BoundaryCurrencyPairMismatch {
                start_pair,
                end_pair,
            } => write!(
                formatter,
                "start boundary pair '{start_pair:?}' does not match end boundary pair '{end_pair:?}'"
            ),
            Self::BoundaryFxRateKindMismatch {
                start_kind,
                end_kind,
            } => write!(
                formatter,
                "start boundary FX rate kind '{start_kind:?}' does not match end boundary FX rate kind '{end_kind:?}'"
            ),
            Self::FxReturnMismatch {
                supplied,
                calculated,
            } => write!(
                formatter,
                "supplied FX return {supplied:?} does not match canonical calculated return {calculated:?}"
            ),
            Self::Core(error) => write!(formatter, "canonical FX calculation error: {error}"),
        }
    }
}

impl Error for FxReturnContractError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Core(error) => Some(error),
            _ => None,
        }
    }
}

impl From<CoreError> for FxReturnContractError {
    fn from(error: CoreError) -> Self {
        Self::Core(error)
    }
}
