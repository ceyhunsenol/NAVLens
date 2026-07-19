use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum CoreError {
    EmptyPortfolio,
    NegativeWeight(f64),
    NonFiniteNumber,
    WeightsDoNotSumToOne(f64),
}

impl Display for CoreError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::EmptyPortfolio => formatter.write_str("portfolio cannot be empty"),
            Self::NegativeWeight(weight) => {
                write!(formatter, "weight cannot be negative: {weight}")
            }
            Self::NonFiniteNumber => formatter.write_str("number must be finite"),
            Self::WeightsDoNotSumToOne(sum) => {
                write!(formatter, "portfolio weights must sum to one; got {sum}")
            }
        }
    }
}

impl Error for CoreError {}
