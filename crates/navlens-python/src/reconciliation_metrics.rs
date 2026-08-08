use navlens_backtest::ReconciliationMetrics;
use pyo3::prelude::*;

/// Python projection of canonical fund return reconciliation metrics calculated by Rust.
#[pyclass(
    name = "ReconciliationMetrics",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct PyReconciliationMetrics {
    inner: ReconciliationMetrics,
}

impl PyReconciliationMetrics {
    pub(crate) const fn from_inner(inner: ReconciliationMetrics) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyReconciliationMetrics {
    #[getter]
    const fn sample_count(&self) -> usize {
        self.inner.sample_count()
    }

    #[getter]
    const fn mean_absolute_residual(&self) -> f64 {
        self.inner.mean_absolute_residual()
    }

    #[getter]
    const fn mean_residual(&self) -> f64 {
        self.inner.mean_residual()
    }

    #[getter]
    const fn root_mean_squared_residual(&self) -> f64 {
        self.inner.root_mean_squared_residual()
    }

    #[getter]
    const fn mean_return_coverage(&self) -> f64 {
        self.inner.mean_return_coverage()
    }

    #[getter]
    const fn full_return_coverage_ratio(&self) -> f64 {
        self.inner.full_return_coverage_ratio()
    }
}
