//! Evaluation metrics for time-ordered fund-return predictions.

mod error;
mod evaluate;
mod metrics;
mod observation;
mod series;

pub use error::BacktestError;
pub use evaluate::evaluate;
pub use metrics::{BacktestMetrics, IntervalMetrics};
pub use observation::Observation;
pub use series::BacktestSeries;
