use crate::error::validation_error;
use crate::fx_adjusted_return_contribution_result::PyFxAdjustedReturnContributionResult;
use crate::fx_rate_series::PyFxRateSeries;
use crate::fx_return_policy::PyFxReturnPolicy;
use crate::portfolio_coverage_report::PyPortfolioCoverageReport;
use crate::return_period::PyReturnPeriod;
use navlens_application::calculate_fx_adjusted_return_contribution as calculate_fx_adjusted_return_contribution_rs;
use pyo3::prelude::*;

#[allow(clippy::trivially_copy_pass_by_ref)]
#[pyfunction]
pub(crate) fn calculate_fx_adjusted_return_contribution(
    report: &PyPortfolioCoverageReport,
    target_period: PyReturnPeriod,
    fx_candidates: Vec<PyFxRateSeries>,
    fx_policy: &PyFxReturnPolicy,
) -> PyResult<PyFxAdjustedReturnContributionResult> {
    let candidates = fx_candidates
        .into_iter()
        .map(PyFxRateSeries::into_inner)
        .collect::<Vec<_>>();

    let result = calculate_fx_adjusted_return_contribution_rs(
        report.inner(),
        target_period.into_inner(),
        &candidates,
        &fx_policy.into_inner(),
    )
    .map_err(validation_error)?;

    Ok(PyFxAdjustedReturnContributionResult::from_inner(result))
}
