use pyo3::prelude::*;

/// Immutable Python projection of a Rust portfolio-return result.
#[pyclass(frozen, module = "navlens._native", skip_from_py_object)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PortfolioReturnEstimate {
    estimated_return_decimal: f64,
}

impl PortfolioReturnEstimate {
    pub(crate) const fn new(estimated_return_decimal: f64) -> Self {
        Self {
            estimated_return_decimal,
        }
    }
}

#[pymethods]
impl PortfolioReturnEstimate {
    #[getter]
    const fn estimated_return_decimal(&self) -> f64 {
        self.estimated_return_decimal
    }

    #[getter]
    const fn estimated_return_percent(&self) -> f64 {
        self.estimated_return_decimal * 100.0
    }

    fn __repr__(&self) -> String {
        format!(
            "PortfolioReturnEstimate(estimated_return_decimal={})",
            self.estimated_return_decimal
        )
    }
}
