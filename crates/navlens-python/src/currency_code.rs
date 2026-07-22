use crate::error::validation_error;
use navlens_core::CurrencyCode;
use pyo3::prelude::*;

/// Python projection of a validated currency code.
#[pyclass(
    name = "CurrencyCode",
    frozen,
    module = "navlens._native",
    eq,
    ord,
    hash,
    from_py_object
)]
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub(crate) struct PyCurrencyCode {
    inner: CurrencyCode,
}

impl PyCurrencyCode {
    pub(crate) const fn from_inner(inner: CurrencyCode) -> Self {
        Self { inner }
    }

    pub(crate) fn into_inner(self) -> CurrencyCode {
        self.inner
    }
}

#[allow(clippy::trivially_copy_pass_by_ref)]
#[pymethods]
impl PyCurrencyCode {
    #[new]
    fn new(value: &str) -> PyResult<Self> {
        CurrencyCode::new(value)
            .map(Self::from_inner)
            .map_err(validation_error)
    }

    #[getter]
    fn code(&self) -> &str {
        self.inner.as_str()
    }

    fn __str__(&self) -> &str {
        self.inner.as_str()
    }

    fn __repr__(&self) -> String {
        format!("CurrencyCode('{}')", self.inner.as_str())
    }
}
