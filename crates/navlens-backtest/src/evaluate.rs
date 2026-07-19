use crate::{BacktestError, BacktestMetrics, Observation};

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
