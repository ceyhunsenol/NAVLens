use crate::fund_return_reconciliation::PyFundReturnReconciliation;
use crate::return_period::PyReturnPeriod;
use navlens_application::FundReturnReconciliationResult;
use pyo3::prelude::*;

/// Python projection of the result of calculating exact-period fund return reconciliation.
#[pyclass(
    name = "FundReturnReconciliationResult",
    frozen,
    module = "navlens._native",
    eq,
    skip_from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyFundReturnReconciliationResult {
    inner: FundReturnReconciliationResult,
}

impl PyFundReturnReconciliationResult {
    pub(crate) const fn from_inner(inner: FundReturnReconciliationResult) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyFundReturnReconciliationResult {
    #[getter]
    fn period(&self) -> PyReturnPeriod {
        PyReturnPeriod::from_inner(self.inner.period())
    }

    #[getter]
    fn reconciliation(&self) -> PyFundReturnReconciliation {
        PyFundReturnReconciliation::from_inner(self.inner.reconciliation())
    }
}
