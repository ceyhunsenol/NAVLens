use navlens_calendar::MarketDate;
use navlens_core::ConfidenceLevel;
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum BacktestError {
    DuplicateTargetDate(MarketDate),
    MixedConfidenceLevels {
        expected: ConfidenceLevel,
        actual: ConfidenceLevel,
    },
    NonChronologicalPredictionDate {
        previous: MarketDate,
        current: MarketDate,
    },
    NonChronologicalTargetDate {
        previous: MarketDate,
        current: MarketDate,
    },
    NoObservations,
    PredictionNotBeforeTarget {
        prediction: MarketDate,
        target: MarketDate,
    },
}

impl Display for BacktestError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::DuplicateTargetDate(date) => {
                write!(formatter, "duplicate backtest target date: {date}")
            }
            Self::MixedConfidenceLevels { expected, actual } => write!(
                formatter,
                "cannot mix confidence levels {} and {} in one backtest series",
                expected.value(),
                actual.value()
            ),
            Self::NonChronologicalPredictionDate { previous, current } => write!(
                formatter,
                "prediction dates must be chronological; {current} follows {previous}"
            ),
            Self::NonChronologicalTargetDate { previous, current } => write!(
                formatter,
                "target dates must be chronological; {current} follows {previous}"
            ),
            Self::NoObservations => {
                formatter.write_str("backtest requires at least one observation")
            }
            Self::PredictionNotBeforeTarget { prediction, target } => write!(
                formatter,
                "prediction date {prediction} must be earlier than target date {target}"
            ),
        }
    }
}

impl Error for BacktestError {}
