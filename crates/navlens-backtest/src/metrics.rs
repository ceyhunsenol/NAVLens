use navlens_core::ConfidenceLevel;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct BacktestMetrics {
    pub sample_count: usize,
    pub mean_absolute_error: f64,
    pub mean_error: f64,
    pub root_mean_squared_error: f64,
    pub direction_accuracy: f64,
    pub interval: Option<IntervalMetrics>,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct IntervalMetrics {
    pub confidence_level: ConfidenceLevel,
    pub sample_count: usize,
    pub coverage: f64,
    pub mean_width: f64,
}
