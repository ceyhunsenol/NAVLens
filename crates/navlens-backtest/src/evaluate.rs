use crate::{BacktestMetrics, BacktestSeries, IntervalMetrics, Observation};

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
        interval: evaluate_intervals(observations),
    }
}

fn evaluate_intervals(observations: &[Observation]) -> Option<IntervalMetrics> {
    let mut confidence_level = None;
    let mut covered = 0usize;
    let mut sample_count = 0usize;
    let mut width_sum = 0.0;

    for observation in observations {
        let Some(interval) = observation.prediction_interval() else {
            continue;
        };
        confidence_level = Some(interval.confidence_level());
        sample_count += 1;
        width_sum += interval.width();
        covered += usize::from(interval.contains(observation.actual_return()));
    }

    let confidence_level = confidence_level?;
    #[allow(clippy::cast_precision_loss)]
    let count = sample_count as f64;
    #[allow(clippy::cast_precision_loss)]
    let coverage = covered as f64 / count;

    Some(IntervalMetrics {
        confidence_level,
        sample_count,
        coverage,
        mean_width: width_sum / count,
    })
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
