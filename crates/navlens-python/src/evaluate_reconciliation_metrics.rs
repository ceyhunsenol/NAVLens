use crate::error::validation_error;
use crate::fund_return_reconciliation_result::PyFundReturnReconciliationResult;
use crate::reconciliation_metrics::PyReconciliationMetrics;
use navlens_backtest::{ReconciliationObservation, ReconciliationSeries, evaluate_reconciliations};
use pyo3::prelude::*;

/// Evaluates a sequence of fund return reconciliation results in Rust.
#[pyfunction]
pub(crate) fn evaluate_reconciliation_metrics(
    results: Vec<PyRef<'_, PyFundReturnReconciliationResult>>,
) -> PyResult<PyReconciliationMetrics> {
    let observations = results
        .into_iter()
        .map(|res| {
            ReconciliationObservation::new(res.inner().period(), res.inner().reconciliation())
        })
        .collect();

    let series = ReconciliationSeries::new(observations).map_err(validation_error)?;
    Ok(PyReconciliationMetrics::from_inner(
        evaluate_reconciliations(&series),
    ))
}
