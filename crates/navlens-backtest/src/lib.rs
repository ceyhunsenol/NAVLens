//! Evaluation metrics for time-ordered fund-return predictions.

use navlens_core::DecimalReturn;
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Observation {
    pub predicted: DecimalReturn,
    pub actual: DecimalReturn,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct BacktestMetrics {
    pub sample_count: usize,
    pub mean_absolute_error: f64,
    pub root_mean_squared_error: f64,
    pub direction_accuracy: f64,
}

/// Computes aggregate metrics for chronological observations.
///
/// # Errors
/// Returns [`BacktestError::NoObservations`] when the input is empty.
pub fn evaluate(observations: &[Observation]) -> Result<BacktestMetrics, BacktestError> {
    if observations.is_empty() {
        return Err(BacktestError::NoObservations);
    }

    let mut absolute_error_sum = 0.0;
    let mut squared_error_sum = 0.0;
    let mut correct_directions = 0usize;

    for observation in observations {
        let predicted = observation.predicted.value();
        let actual = observation.actual.value();
        let error = predicted - actual;
        absolute_error_sum += error.abs();
        squared_error_sum += error * error;

        if predicted.total_cmp(&0.0) == actual.total_cmp(&0.0) {
            correct_directions += 1;
        }
    }

    #[allow(clippy::cast_precision_loss)]
    let count = observations.len() as f64;
    #[allow(clippy::cast_precision_loss)]
    let direction_accuracy = correct_directions as f64 / count;

    Ok(BacktestMetrics {
        sample_count: observations.len(),
        mean_absolute_error: absolute_error_sum / count,
        root_mean_squared_error: (squared_error_sum / count).sqrt(),
        direction_accuracy,
    })
}

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

#[cfg(test)]
mod tests {
    use super::*;

    fn return_of(value: f64) -> DecimalReturn {
        DecimalReturn::new(value).expect("test return should be finite")
    }

    #[test]
    fn evaluates_prediction_metrics() {
        let observations = [
            Observation {
                predicted: return_of(0.01),
                actual: return_of(0.02),
            },
            Observation {
                predicted: return_of(-0.02),
                actual: return_of(-0.01),
            },
            Observation {
                predicted: return_of(0.01),
                actual: return_of(-0.01),
            },
        ];

        let metrics = evaluate(&observations).expect("non-empty observations");
        assert_eq!(metrics.sample_count, 3);
        assert!((metrics.mean_absolute_error - (0.04 / 3.0)).abs() < 1e-12);
        assert!((metrics.root_mean_squared_error - (0.0006_f64 / 3.0).sqrt()).abs() < 1e-12);
        assert!((metrics.direction_accuracy - (2.0 / 3.0)).abs() < 1e-12);
    }

    #[test]
    fn rejects_empty_backtest() {
        assert_eq!(evaluate(&[]), Err(BacktestError::NoObservations));
    }
}
