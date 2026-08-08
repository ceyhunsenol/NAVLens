use crate::error::validation_error;
use crate::fund_return_reconciliation_result::PyFundReturnReconciliationResult;
use crate::fx_adjusted_return_contribution_result::PyFxAdjustedReturnContributionResult;
use crate::period_decimal_return::PyPeriodDecimalReturn;
use crate::return_contribution_result::PyReturnContributionResult;
use navlens_application::reconcile_fund_return as app_reconcile_fund_return;
use navlens_application::reconcile_fx_adjusted_fund_return as app_reconcile_fx_adjusted_fund_return;
use pyo3::prelude::*;

/// Reconciles a published fund return with its observed portfolio contribution.
#[pyfunction]
#[pyo3(signature = (published_fund_return, contribution_result))]
pub(crate) fn reconcile_fund_return(
    published_fund_return: PyPeriodDecimalReturn,
    contribution_result: &PyReturnContributionResult,
) -> PyResult<PyFundReturnReconciliationResult> {
    let result = app_reconcile_fund_return(
        published_fund_return.into_inner(),
        contribution_result.inner(),
    )
    .map_err(validation_error)?;

    Ok(PyFundReturnReconciliationResult::from_inner(result))
}

/// Reconciles a published fund return with its FX-adjusted observed portfolio contribution.
#[pyfunction]
pub(crate) fn reconcile_fx_adjusted_fund_return(
    published_fund_return: PyPeriodDecimalReturn,
    contribution_result: &PyFxAdjustedReturnContributionResult,
) -> PyResult<PyFundReturnReconciliationResult> {
    let result = app_reconcile_fx_adjusted_fund_return(
        published_fund_return.into_inner(),
        contribution_result.inner(),
    )
    .map_err(validation_error)?;

    Ok(PyFundReturnReconciliationResult::from_inner(result))
}
