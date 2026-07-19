use navlens_core::CoreError;
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum ApplicationError {
    InvalidEstimateInput(CoreError),
}

impl Display for ApplicationError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidEstimateInput(error) => {
                write!(formatter, "invalid portfolio estimate input: {error}")
            }
        }
    }
}

impl Error for ApplicationError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::InvalidEstimateInput(error) => Some(error),
        }
    }
}

impl From<CoreError> for ApplicationError {
    fn from(error: CoreError) -> Self {
        Self::InvalidEstimateInput(error)
    }
}
