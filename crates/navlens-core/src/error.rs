use crate::gross_return_component::GrossReturnComponent;
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum CoreError {
    ConfidenceLevelOutOfRange(f64),
    EmptyInstrumentId,
    EmptyPortfolio,
    EmptyFundId,
    DeclaredWeightExceedsFundTotal(f64),
    ExpenseRateOutOfRange(f64),
    FundIdContainsControlCharacter,
    FundIdContainsWhitespace,
    FundIdTooLong(usize),
    InstrumentIdContainsControlCharacter,
    InstrumentIdContainsWhitespace,
    InstrumentIdTooLong(usize),
    NonFiniteNumber,
    PortfolioWeightOutOfRange(f64),
    PredictionIntervalBounds {
        lower: f64,
        upper: f64,
    },
    UnitPriceNotPositive(f64),
    WeightsDoNotSumToOne(f64),
    InvalidCurrencyCode,
    ReturnCoverageExceedsFundTotal(f64),
    FxRateNotPositive(f64),
    IdenticalCurrencyPair,
    NonPositiveGrossReturn {
        component: GrossReturnComponent,
        decimal_return: f64,
    },
}

impl Display for CoreError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ConfidenceLevelOutOfRange(level) => write!(
                formatter,
                "confidence level must be strictly between zero and one; got {level}"
            ),
            Self::DeclaredWeightExceedsFundTotal(total) => write!(
                formatter,
                "declared portfolio weight cannot exceed 1.0; got {total}"
            ),
            Self::EmptyInstrumentId => formatter.write_str("instrument identifier cannot be empty"),
            Self::EmptyPortfolio => formatter.write_str("portfolio cannot be empty"),
            Self::EmptyFundId => formatter.write_str("fund identifier cannot be empty"),
            Self::ExpenseRateOutOfRange(rate) => {
                write!(
                    formatter,
                    "expense rate must be between zero and one; got {rate}"
                )
            }
            Self::FundIdContainsControlCharacter => {
                formatter.write_str("fund identifier cannot contain control characters")
            }
            Self::FundIdContainsWhitespace => {
                formatter.write_str("fund identifier cannot contain whitespace")
            }
            Self::FundIdTooLong(length) => write!(
                formatter,
                "fund identifier cannot exceed 64 characters; got {length}"
            ),
            Self::InstrumentIdContainsControlCharacter => {
                formatter.write_str("instrument identifier cannot contain control characters")
            }
            Self::InstrumentIdContainsWhitespace => {
                formatter.write_str("instrument identifier cannot contain whitespace")
            }
            Self::InstrumentIdTooLong(length) => write!(
                formatter,
                "instrument identifier cannot exceed 64 characters; got {length}"
            ),
            Self::NonFiniteNumber => formatter.write_str("number must be finite"),
            Self::PortfolioWeightOutOfRange(weight) => {
                write!(
                    formatter,
                    "portfolio weight must be between zero and one; got {weight}"
                )
            }
            Self::PredictionIntervalBounds { lower, upper } => write!(
                formatter,
                "prediction interval lower bound {lower} exceeds upper bound {upper}"
            ),
            Self::UnitPriceNotPositive(price) => {
                write!(
                    formatter,
                    "unit price must be strictly positive; got {price}"
                )
            }
            Self::WeightsDoNotSumToOne(sum) => {
                write!(formatter, "portfolio weights must sum to one; got {sum}")
            }
            Self::InvalidCurrencyCode => {
                formatter.write_str("currency code must be exactly three uppercase ASCII letters")
            }
            Self::ReturnCoverageExceedsFundTotal(total) => write!(
                formatter,
                "return coverage portfolio weight cannot exceed 1.0; got {total}"
            ),
            Self::FxRateNotPositive(rate) => {
                write!(
                    formatter,
                    "foreign exchange rate must be strictly positive; got {rate}"
                )
            }
            Self::IdenticalCurrencyPair => {
                formatter.write_str("currency pair base and quote currencies cannot be identical")
            }
            Self::NonPositiveGrossReturn {
                component,
                decimal_return,
            } => {
                let component_str = match component {
                    GrossReturnComponent::Security => "security",
                    GrossReturnComponent::ForeignExchange => "foreign exchange",
                };
                write!(
                    formatter,
                    "{component_str} gross return factor must be positive; got decimal return {decimal_return}"
                )
            }
        }
    }
}

impl Error for CoreError {}
