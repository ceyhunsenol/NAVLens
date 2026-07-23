use navlens_calendar::PricingError;
use navlens_core::CoreError;
use std::error::Error;
use std::fmt::{Display, Formatter};

/// Errors that can occur when calculating aligned portfolio return contribution.
#[derive(Clone, Debug, PartialEq)]
pub enum CalculateReturnContributionError {
    Pricing(PricingError),
    Domain(CoreError),
}

impl Display for CalculateReturnContributionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Pricing(e) => write!(f, "pricing error during contribution calculation: {e}"),
            Self::Domain(e) => write!(f, "domain error during contribution calculation: {e}"),
        }
    }
}

impl Error for CalculateReturnContributionError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Pricing(e) => Some(e),
            Self::Domain(e) => Some(e),
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
