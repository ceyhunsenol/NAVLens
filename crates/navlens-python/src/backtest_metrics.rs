use navlens_backtest::{BacktestMetrics, IntervalMetrics};
use pyo3::prelude::*;

/// Python projection of interval-quality metrics calculated by Rust.
#[pyclass(
    name = "IntervalMetrics",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct PyIntervalMetrics {
    inner: IntervalMetrics,
}

impl PyIntervalMetrics {
    const fn from_inner(inner: IntervalMetrics) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyIntervalMetrics {
    #[getter]
    const fn confidence_level(&self) -> f64 {
        self.inner.confidence_level.value()
    }

    #[getter]
    const fn sample_count(&self) -> usize {
        self.inner.sample_count
    }

    #[getter]
    const fn coverage(&self) -> f64 {
        self.inner.coverage
    }

    #[getter]
    const fn mean_width(&self) -> f64 {
        self.inner.mean_width
    }
}

/// Python projection of canonical backtest metrics calculated by Rust.
#[pyclass(
    name = "BacktestMetrics",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct PyBacktestMetrics {
    inner: BacktestMetrics,
}

impl PyBacktestMetrics {
    pub(crate) const fn from_inner(inner: BacktestMetrics) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyBacktestMetrics {
    #[getter]
    const fn sample_count(&self) -> usize {
        self.inner.sample_count
    }

    #[getter]
    const fn mean_absolute_error(&self) -> f64 {
        self.inner.mean_absolute_error
    }

    #[getter]
    const fn mean_error(&self) -> f64 {
        self.inner.mean_error
    }

    #[getter]
    const fn root_mean_squared_error(&self) -> f64 {
        self.inner.root_mean_squared_error
    }

    #[getter]
    const fn direction_accuracy(&self) -> f64 {
        self.inner.direction_accuracy
    }

    #[getter]
    fn interval(&self) -> Option<PyIntervalMetrics> {
        self.inner.interval.map(PyIntervalMetrics::from_inner)
    }
}
