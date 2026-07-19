use crate::{BacktestMetrics, BacktestSeries};

/// Computes aggregate metrics for a validated chronological series.
#[must_use]
pub fn evaluate(series: &BacktestSeries) -> BacktestMetrics {
    let observations = series.observations();
    let mut absolute_error_sum = 0.0;
    let mut error_sum = 0.0;
    let mut squared_error_sum = 0.0;
    let mut correct_directions = 0usize;

    for observation in observations {
        let predicted = observation.predicted_return().value();
        let actual = observation.actual_return().value();
        let error = predicted - actual;
        absolute_error_sum += error.abs();
        error_sum += error;
        squared_error_sum += error * error;

        if direction(predicted) == direction(actual) {
            correct_directions += 1;
        }
    }

    #[allow(clippy::cast_precision_loss)]
    let count = observations.len() as f64;
    #[allow(clippy::cast_precision_loss)]
    let direction_accuracy = correct_directions as f64 / count;

    BacktestMetrics {
        sample_count: observations.len(),
        mean_absolute_error: absolute_error_sum / count,
        mean_error: error_sum / count,
        root_mean_squared_error: (squared_error_sum / count).sqrt(),
        direction_accuracy,
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Direction {
    Negative,
    Flat,
    Positive,
}

fn direction(value: f64) -> Direction {
    if value > 0.0 {
        Direction::Positive
    } else if value < 0.0 {
        Direction::Negative
    } else {
        Direction::Flat
    }
}
