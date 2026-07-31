use crate::error::validation_error;
use navlens_core::FxRate;
use pyo3::prelude::*;

/// Python projection of a positive, finite foreign exchange rate value.
#[pyclass(
    name = "FxRate",
    frozen,
    module = "navlens._native",
    eq,
    from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct PyFxRate {
    inner: FxRate,
}

impl PyFxRate {
    pub(crate) const fn from_inner(inner: FxRate) -> Self {
        Self { inner }
    }

    pub(crate) const fn into_inner(self) -> FxRate {
        self.inner
    }
}

#[allow(clippy::trivially_copy_pass_by_ref)]
#[pymethods]
impl PyFxRate {
    #[new]
    fn new(quote_currency_per_one_base_currency: f64) -> PyResult<Self> {
        FxRate::new(quote_currency_per_one_base_currency)
            .map(Self::from_inner)
            .map_err(validation_error)
    }

    #[getter]
    fn quote_currency_per_one_base_currency(&self) -> f64 {
        self.inner.quote_currency_per_one_base_currency()
    }

    fn __repr__(&self) -> String {
        format!(
            "FxRate({})",
            self.inner.quote_currency_per_one_base_currency()
        )
    }
}
