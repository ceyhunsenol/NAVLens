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
    InvalidReturnPeriod {
        period_start_date: MarketDate,
        period_end_date: MarketDate,
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
            Self::InvalidReturnPeriod {
                period_start_date,
                period_end_date,
            } => write!(
                formatter,
                "return period start must precede end; {period_start_date} is on or after {period_end_date}"
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
