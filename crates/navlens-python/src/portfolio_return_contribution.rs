use navlens_core::PortfolioReturnContribution;
use pyo3::prelude::*;

/// Python projection of the observed return contribution of a portfolio's covered holdings.
#[pyclass(
    name = "PortfolioReturnContribution",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyPortfolioReturnContribution {
    inner: PortfolioReturnContribution,
}

impl PyPortfolioReturnContribution {
    pub(crate) const fn from_inner(inner: PortfolioReturnContribution) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyPortfolioReturnContribution {
    #[getter]
    fn observed_contribution(&self) -> f64 {
        self.inner.observed_contribution().value()
    }

    #[getter]
    fn return_coverage(&self) -> f64 {
        self.inner.return_coverage().value()
    }

    #[getter]
    fn has_full_coverage(&self) -> bool {
        self.inner.has_full_coverage()
    }

    fn __repr__(&self) -> String {
        format!(
            "PortfolioReturnContribution(observed_contribution={}, return_coverage={})",
            self.inner.observed_contribution().value(),
            self.inner.return_coverage().value()
        )
    }
}
