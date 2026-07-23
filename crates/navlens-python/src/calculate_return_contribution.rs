use crate::error::validation_error;
use crate::portfolio_coverage_report::PyPortfolioCoverageReport;
use crate::return_contribution_result::PyReturnContributionResult;
use crate::return_period::PyReturnPeriod;
use navlens_application::calculate_return_contribution as core_calculate_return_contribution;
use pyo3::prelude::*;

#[pyfunction]
pub(crate) fn calculate_return_contribution(
    report: &PyPortfolioCoverageReport,
    target_period: PyReturnPeriod,
) -> PyResult<PyReturnContributionResult> {
    let result = core_calculate_return_contribution(report.inner(), target_period.into_inner())
        .map_err(validation_error)?;

    Ok(PyReturnContributionResult::from_inner(result))
}
