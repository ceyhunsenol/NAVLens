use crate::{MarketDate, PriceAdjustment};
use navlens_core::{CoreError, CurrencyCode, CurrencyPair, FxRateKind, InstrumentId};
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
    EmptyFxRateSeries,
    DuplicateFxRateDate(MarketDate),
    NonChronologicalFxRateDate {
        previous: MarketDate,
        current: MarketDate,
    },
    MixedCurrencyPair {
        expected: CurrencyPair,
        found: CurrencyPair,
    },
    MixedFxRateKind {
        expected: FxRateKind,
        found: FxRateKind,
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
            Self::EmptyFxRateSeries => formatter.write_str("FX rate series cannot be empty"),
            Self::DuplicateFxRateDate(date) => write!(formatter, "duplicate FX rate for {date}"),
            Self::NonChronologicalFxRateDate { previous, current } => write!(
                formatter,
                "FX rate dates must increase; {current} follows {previous}"
            ),
            Self::MixedCurrencyPair { expected, found } => write!(
                formatter,
                "all observations in an FX rate series must share the same currency pair; expected {expected:?}, found {found:?}"
            ),
            Self::MixedFxRateKind { expected, found } => write!(
                formatter,
                "all observations in an FX rate series must share the same rate kind; expected {expected:?}, found {found:?}"
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
