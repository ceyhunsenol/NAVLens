use crate::MarketDate;
use navlens_core::CoreError;
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum PricingError {
    DuplicatePriceDate(MarketDate),
    InsufficientPriceObservations(usize),
    NonChronologicalPriceDate {
        previous: MarketDate,
        current: MarketDate,
    },
    ReturnCalculation(CoreError),
}

impl Display for PricingError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::DuplicatePriceDate(date) => write!(formatter, "duplicate unit price for {date}"),
            Self::InsufficientPriceObservations(count) => write!(
                formatter,
                "at least two price observations are required; got {count}"
            ),
            Self::NonChronologicalPriceDate { previous, current } => write!(
                formatter,
                "price dates must increase; {current} follows {previous}"
            ),
            Self::ReturnCalculation(error) => Display::fmt(error, formatter),
        }
    }
}

impl Error for PricingError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::ReturnCalculation(error) => Some(error),
            _ => None,
        }
    }
}
