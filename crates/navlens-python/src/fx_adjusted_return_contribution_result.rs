use crate::fx_adjusted_component_contribution::PyFxAdjustedComponentContribution;
use crate::portfolio_return_contribution::PyPortfolioReturnContribution;
use crate::return_coverage_gap::PyReturnCoverageGap;
use crate::return_period::PyReturnPeriod;
use crate::uncovered_holding::PyUncoveredHolding;
use navlens_application::FxAdjustedReturnContributionResult;
use pyo3::prelude::*;

#[pyclass(
    name = "FxAdjustedReturnContributionResult",
    frozen,
    module = "navlens._native",
    eq,
    from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyFxAdjustedReturnContributionResult {
    inner: FxAdjustedReturnContributionResult,
}

impl PyFxAdjustedReturnContributionResult {
    pub(crate) const fn from_inner(inner: FxAdjustedReturnContributionResult) -> Self {
        Self { inner }
    }

    pub(crate) const fn inner(&self) -> &FxAdjustedReturnContributionResult {
        &self.inner
    }
}

#[pymethods]
impl PyFxAdjustedReturnContributionResult {
    #[getter]
    fn period(&self) -> PyReturnPeriod {
        PyReturnPeriod::from_inner(*self.inner.period())
    }

    #[getter]
    fn component_contributions(&self) -> Vec<PyFxAdjustedComponentContribution> {
        self.inner
            .component_contributions()
            .iter()
            .cloned()
            .map(PyFxAdjustedComponentContribution::from_inner)
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
