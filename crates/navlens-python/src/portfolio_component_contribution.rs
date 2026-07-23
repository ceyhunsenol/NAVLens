use navlens_core::PortfolioComponentContribution;
use pyo3::prelude::*;

/// Python projection of the weighted return contribution of a single portfolio component.
#[pyclass(
    name = "PortfolioComponentContribution",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyPortfolioComponentContribution {
    inner: PortfolioComponentContribution,
}

impl PyPortfolioComponentContribution {
    pub(crate) const fn from_inner(inner: PortfolioComponentContribution) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyPortfolioComponentContribution {
    #[getter]
    fn weight(&self) -> f64 {
        self.inner.weight().value()
    }

    #[getter]
    fn market_return(&self) -> f64 {
        self.inner.market_return().value()
    }

    #[getter]
    fn weighted_contribution(&self) -> f64 {
        self.inner.weighted_contribution().value()
    }

    fn __repr__(&self) -> String {
        format!(
            "PortfolioComponentContribution(weight={}, market_return={}, weighted_contribution={})",
            self.inner.weight().value(),
            self.inner.market_return().value(),
            self.inner.weighted_contribution().value()
        )
    }
}
