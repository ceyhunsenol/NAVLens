use crate::alignment_policy::PyAlignmentPolicy;
use crate::covered_holding_price::PyCoveredHoldingPrice;
use crate::uncovered_holding::PyUncoveredHolding;
use navlens_application::PortfolioCoverageReport;
use pyo3::prelude::*;

#[pyclass(
    name = "PortfolioCoverageReport",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone)]
pub(crate) struct PyPortfolioCoverageReport {
    inner: PortfolioCoverageReport,
}

impl PyPortfolioCoverageReport {
    pub(crate) const fn from_inner(inner: PortfolioCoverageReport) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyPortfolioCoverageReport {
    #[getter]
    fn covered(&self) -> Vec<PyCoveredHoldingPrice> {
        self.inner
            .covered()
            .iter()
            .cloned()
            .map(PyCoveredHoldingPrice::from_inner)
            .collect()
    }

    #[getter]
    fn uncovered_listed(&self) -> Vec<PyUncoveredHolding> {
        self.inner
            .uncovered_listed()
            .iter()
            .cloned()
            .map(PyUncoveredHolding::from_inner)
            .collect()
    }

    #[getter]
    fn declared_weight(&self) -> f64 {
        self.inner.weights().declared_weight().value()
    }

    #[getter]
    fn covered_weight(&self) -> f64 {
        self.inner.weights().covered_weight().value()
    }

    #[getter]
    fn uncovered_listed_weight(&self) -> f64 {
        self.inner.weights().uncovered_listed_weight().value()
    }

    #[getter]
    fn unrepresented_weight(&self) -> f64 {
        self.inner.weights().unrepresented_weight().value()
    }

    #[getter]
    fn total_uncovered_weight(&self) -> f64 {
        self.inner.weights().total_uncovered_weight().value()
    }

    #[getter]
    fn coverage_ratio(&self) -> f64 {
        self.inner.weights().coverage_ratio().value()
    }

    #[getter]
    fn policy(&self) -> PyAlignmentPolicy {
        PyAlignmentPolicy::from_inner(self.inner.policy().clone())
    }
}
