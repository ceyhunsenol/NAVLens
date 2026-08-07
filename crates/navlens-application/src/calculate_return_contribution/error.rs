use crate::calculate_fx_adjusted_return_contribution::FxReturnContractError;
use navlens_calendar::{MarketDate, PricingError};
use navlens_core::{CoreError, CurrencyPair, FxRateKind};
use std::error::Error;
use std::fmt::{Display, Formatter};

/// Errors that can occur when calculating aligned portfolio return contribution.
#[derive(Clone, Debug, PartialEq)]
pub enum CalculateReturnContributionError {
    Pricing(PricingError),
    Domain(CoreError),
    DuplicateFxCandidate {
        pair: CurrencyPair,
        kind: FxRateKind,
    },
    InvalidStalenessConversion {
        requested_date: MarketDate,
        observation_date: MarketDate,
        staleness: i64,
    },
    MissingFxEndAfterStartInvariant {
        requested_date: MarketDate,
    },
    FxContract(FxReturnContractError),
}

impl Display for CalculateReturnContributionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Pricing(e) => write!(f, "pricing error during contribution calculation: {e}"),
            Self::Domain(e) => write!(f, "domain error during contribution calculation: {e}"),
            Self::DuplicateFxCandidate { pair, kind } => write!(
                f,
                "duplicate FX candidate identity for pair {pair:?} and kind {kind:?}",
            ),
            Self::InvalidStalenessConversion {
                requested_date,
                observation_date,
                staleness,
            } => {
                write!(
                    f,
                    "invalid staleness {staleness} between FX observation {observation_date} and requested boundary {requested_date}"
                )
            }
            Self::MissingFxEndAfterStartInvariant { requested_date } => write!(
                f,
                "FX series lost its selected start observation before end boundary {requested_date}"
            ),
            Self::FxContract(e) => {
                write!(f, "FX contract error during contribution calculation: {e}")
            }
        }
    }
}

impl Error for CalculateReturnContributionError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Pricing(e) => Some(e),
            Self::Domain(e) => Some(e),
            Self::DuplicateFxCandidate { .. }
            | Self::InvalidStalenessConversion { .. }
            | Self::MissingFxEndAfterStartInvariant { .. } => None,
            Self::FxContract(e) => Some(e),
        }
    }
}

impl From<PricingError> for CalculateReturnContributionError {
    fn from(error: PricingError) -> Self {
        Self::Pricing(error)
    }
}

impl From<CoreError> for CalculateReturnContributionError {
    fn from(error: CoreError) -> Self {
        Self::Domain(error)
    }
}

impl From<FxReturnContractError> for CalculateReturnContributionError {
    fn from(error: FxReturnContractError) -> Self {
        Self::FxContract(error)
    }
}
