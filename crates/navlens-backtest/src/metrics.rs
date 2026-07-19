#[derive(Clone, Copy, Debug, PartialEq)]
pub struct BacktestMetrics {
    pub sample_count: usize,
    pub mean_absolute_error: f64,
    pub mean_error: f64,
    pub root_mean_squared_error: f64,
    pub direction_accuracy: f64,
}
