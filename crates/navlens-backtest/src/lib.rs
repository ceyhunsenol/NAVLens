//! Evaluation metrics for time-ordered fund-return predictions and reconciliations.

mod error;
mod evaluate;
mod metrics;
mod observation;
mod reconciliation;
mod series;

pub use error::BacktestError;
pub use evaluate::evaluate;
pub use metrics::{BacktestMetrics, IntervalMetrics};
pub use observation::Observation;
pub use reconciliation::{
    ReconciliationMetrics, ReconciliationObservation, ReconciliationSeries,
    evaluate_reconciliations,
};
pub use series::BacktestSeries;
