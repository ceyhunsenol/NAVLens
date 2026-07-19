//! Evaluation metrics for time-ordered fund-return predictions.

mod error;
mod evaluate;
mod metrics;
mod observation;

pub use error::BacktestError;
pub use evaluate::evaluate;
pub use metrics::BacktestMetrics;
pub use observation::Observation;
