use crate::backtest_metrics::PyBacktestMetrics;
use crate::backtest_observation::PyBacktestObservation;
use crate::error::validation_error;
use navlens_backtest::{BacktestSeries, evaluate};
use navlens_core::FundId;
use pyo3::prelude::*;

/// Validates and evaluates a chronological prediction series in Rust.
#[pyfunction]
pub(crate) fn evaluate_backtest(
    fund_id: String,
    observations: Vec<PyBacktestObservation>,
) -> PyResult<PyBacktestMetrics> {
    let fund_id = FundId::new(fund_id).map_err(validation_error)?;
    let observations = observations
        .into_iter()
        .map(PyBacktestObservation::into_inner)
        .collect();
    let series = BacktestSeries::new(fund_id, observations).map_err(validation_error)?;

    Ok(PyBacktestMetrics::from_inner(evaluate(&series)))
}
