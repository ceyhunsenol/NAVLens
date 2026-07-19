use navlens_calendar::MarketDate;
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PredictionMetadataField {
    ModelName,
    ModelVersion,
    FeatureSetVersion,
}

impl Display for PredictionMetadataField {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(match self {
            Self::ModelName => "model name",
            Self::ModelVersion => "model version",
            Self::FeatureSetVersion => "feature-set version",
        })
    }
}

#[derive(Clone, Debug, PartialEq)]
pub enum PredictionError {
    DataAfterGeneration {
        data_as_of_unix_seconds: i64,
        generated_at_unix_seconds: i64,
    },
    EmptyMetadata(PredictionMetadataField),
    ExpectedReturnOutsideInterval {
        expected: f64,
        lower: f64,
        upper: f64,
    },
    MetadataContainsControlCharacter(PredictionMetadataField),
    PredictionNotBeforeTarget {
        prediction: MarketDate,
        target: MarketDate,
    },
}

impl Display for PredictionError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::DataAfterGeneration {
                data_as_of_unix_seconds,
                generated_at_unix_seconds,
            } => write!(
                formatter,
                "data timestamp {data_as_of_unix_seconds} must not be later than prediction generation timestamp {generated_at_unix_seconds}"
            ),
            Self::EmptyMetadata(field) => write!(formatter, "{field} must not be empty"),
            Self::ExpectedReturnOutsideInterval {
                expected,
                lower,
                upper,
            } => write!(
                formatter,
                "expected return {expected} must be inside prediction interval [{lower}, {upper}]"
            ),
            Self::MetadataContainsControlCharacter(field) => {
                write!(formatter, "{field} must not contain control characters")
            }
            Self::PredictionNotBeforeTarget { prediction, target } => write!(
                formatter,
                "prediction date {prediction} must be earlier than target date {target}"
            ),
        }
    }
}

impl Error for PredictionError {}
