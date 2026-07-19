use crate::error::validation_error;
use navlens_core::UnitPrice;
use pyo3::prelude::*;

/// Python projection of a validated fund unit price.
#[pyclass(name = "UnitPrice", frozen, module = "navlens._native", from_py_object)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyUnitPrice {
    inner: UnitPrice,
}

impl PyUnitPrice {
    pub(crate) const fn from_inner(inner: UnitPrice) -> Self {
        Self { inner }
    }

    pub(crate) const fn into_inner(self) -> UnitPrice {
        self.inner
    }
}

#[pymethods]
impl PyUnitPrice {
    #[new]
    fn new(value: f64) -> PyResult<Self> {
        UnitPrice::new(value)
            .map(Self::from_inner)
            .map_err(validation_error)
    }

    #[getter]
    const fn value(&self) -> f64 {
        self.inner.value()
    }

    fn __repr__(&self) -> String {
        format!("UnitPrice({})", self.inner.value())
    }
}
