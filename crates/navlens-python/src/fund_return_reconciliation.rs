use crate::portfolio_return_contribution::PyPortfolioReturnContribution;
use navlens_core::FundReturnReconciliation;
use pyo3::prelude::*;

/// Python projection of the result of reconciling a published fund return with its observed portfolio contribution.
#[pyclass(
    name = "FundReturnReconciliation",
    frozen,
    module = "navlens._native",
    eq,
    skip_from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyFundReturnReconciliation {
    inner: FundReturnReconciliation,
}

impl PyFundReturnReconciliation {
    pub(crate) const fn from_inner(inner: FundReturnReconciliation) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyFundReturnReconciliation {
    #[getter]
    fn published_fund_return(&self) -> f64 {
        self.inner.published_fund_return().value()
    }

    #[getter]
    fn observed_portfolio_contribution(&self) -> PyPortfolioReturnContribution {
        PyPortfolioReturnContribution::from_inner(self.inner.observed_portfolio_contribution())
    }

    #[getter]
    fn reconciliation_residual(&self) -> f64 {
        self.inner.reconciliation_residual().value()
    }
}
