use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum BacktestError {
    NoObservations,
}

impl Display for BacktestError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        formatter.write_str("backtest requires at least one observation")
    }
}

impl Error for BacktestError {}
