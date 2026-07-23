use navlens_calendar::ReturnPeriod;
use navlens_core::CoreError;

/// Error type for fund return reconciliation.
#[derive(Debug, Clone, PartialEq)]
pub enum ReconcileFundReturnError {
    /// Period mismatch between the published fund return and the portfolio contribution.
    PeriodMismatch {
        published_period: ReturnPeriod,
        contribution_period: ReturnPeriod,
    },
    /// A core domain validation or arithmetic failure.
    Domain(CoreError),
}

impl std::fmt::Display for ReconcileFundReturnError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::PeriodMismatch {
                published_period,
                contribution_period,
            } => write!(
                f,
                "fund return period ({published_period:?}) does not match portfolio contribution period ({contribution_period:?})"
            ),
            Self::Domain(err) => write!(f, "domain validation failed: {err}"),
        }
    }
}

impl std::error::Error for ReconcileFundReturnError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::PeriodMismatch { .. } => None,
            Self::Domain(err) => Some(err),
        }
    }
}

impl From<CoreError> for ReconcileFundReturnError {
    fn from(err: CoreError) -> Self {
        Self::Domain(err)
    }
}
