use crate::currency_code::PyCurrencyCode;
use crate::error::validation_error;
use navlens_core::CurrencyPair;
use pyo3::prelude::*;

/// Python projection of a directional currency pair.
#[pyclass(
    name = "CurrencyPair",
    frozen,
    module = "navlens._native",
    eq,
    ord,
    hash,
    from_py_object
)]
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub(crate) struct PyCurrencyPair {
    inner: CurrencyPair,
}

impl PyCurrencyPair {
    pub(crate) fn from_inner(inner: CurrencyPair) -> Self {
        Self { inner }
    }

    pub(crate) fn into_inner(self) -> CurrencyPair {
        self.inner
    }
}

#[pymethods]
impl PyCurrencyPair {
    #[new]
    fn new(base_currency: PyCurrencyCode, quote_currency: PyCurrencyCode) -> PyResult<Self> {
        CurrencyPair::new(base_currency.into_inner(), quote_currency.into_inner())
            .map(Self::from_inner)
            .map_err(validation_error)
    }

    #[getter]
    fn base_currency(&self) -> PyCurrencyCode {
        PyCurrencyCode::from_inner(self.inner.base_currency().clone())
    }

    #[getter]
    fn quote_currency(&self) -> PyCurrencyCode {
        PyCurrencyCode::from_inner(self.inner.quote_currency().clone())
    }

    fn __repr__(&self) -> String {
        format!(
            "CurrencyPair(base_currency=CurrencyCode('{}'), quote_currency=CurrencyCode('{}'))",
            self.inner.base_currency().as_str(),
            self.inner.quote_currency().as_str()
        )
    }
}
