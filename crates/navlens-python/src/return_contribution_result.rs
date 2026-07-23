use crate::component_contribution::PyComponentContribution;
use crate::portfolio_return_contribution::PyPortfolioReturnContribution;
use crate::return_coverage_gap::PyReturnCoverageGap;
use crate::return_period::PyReturnPeriod;
use crate::uncovered_holding::PyUncoveredHolding;
use navlens_application::ReturnContributionResult;
use pyo3::prelude::*;

/// Python projection of the result of calculating the aligned portfolio return contribution.
#[pyclass(
    name = "ReturnContributionResult",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyReturnContributionResult {
    inner: ReturnContributionResult,
}

impl PyReturnContributionResult {
    pub(crate) fn from_inner(inner: ReturnContributionResult) -> Self {
        Self { inner }
    }

    pub(crate) const fn inner(&self) -> &ReturnContributionResult {
        &self.inner
    }
}

#[pymethods]
impl PyReturnContributionResult {
    #[getter]
    fn period(&self) -> PyReturnPeriod {
        PyReturnPeriod::from_inner(*self.inner.period())
    }

    #[getter]
    fn component_contributions(&self) -> Vec<PyComponentContribution> {
        self.inner
            .component_contributions()
            .iter()
            .cloned()
            .map(PyComponentContribution::from_inner)
            .collect()
    }

    #[getter]
    fn observed_contribution(&self) -> PyPortfolioReturnContribution {
        PyPortfolioReturnContribution::from_inner(*self.inner.observed_contribution())
    }

    #[getter]
    fn price_coverage(&self) -> f64 {
        self.inner.price_coverage().value()
    }

    #[getter]
    fn price_gaps(&self) -> Vec<PyUncoveredHolding> {
        self.inner
            .price_gaps()
            .iter()
            .cloned()
            .map(PyUncoveredHolding::from_inner)
            .collect()
    }

    #[getter]
    fn return_gaps(&self) -> Vec<PyReturnCoverageGap> {
        self.inner
            .return_gaps()
            .iter()
            .cloned()
            .map(PyReturnCoverageGap::from_inner)
            .collect()
    }
}
