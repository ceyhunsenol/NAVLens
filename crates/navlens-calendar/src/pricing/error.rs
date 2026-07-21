use crate::{MarketDate, PriceAdjustment};
use navlens_core::{CoreError, CurrencyCode, InstrumentId};
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Clone, Debug, PartialEq)]
pub enum PricingError {
    DuplicatePriceDate(MarketDate),
    InsufficientPriceObservations(usize),
    NonChronologicalPriceDate {
        previous: MarketDate,
        current: MarketDate,
    },
    ReturnCalculation(CoreError),
    MixedInstrumentId {
        expected: InstrumentId,
        found: InstrumentId,
    },
    MixedCurrencyCode {
        expected: CurrencyCode,
        found: CurrencyCode,
    },
    MixedPriceAdjustment {
        expected: PriceAdjustment,
        found: PriceAdjustment,
    },
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
            Self::MixedInstrumentId { expected, found } => write!(
                formatter,
                "all observations in a series must share the same instrument ID; expected {expected}, found {found}"
            ),
            Self::MixedCurrencyCode { expected, found } => write!(
                formatter,
                "all observations in a series must share the same currency; expected {expected}, found {found}"
            ),
            Self::MixedPriceAdjustment { expected, found } => write!(
                formatter,
                "all observations in a series must share the same price adjustment; expected {expected:?}, found {found:?}"
            ),
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
