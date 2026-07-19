use crate::error::validation_error;
use navlens_calendar::MarketDate;
use pyo3::prelude::*;

/// Python projection of a validated market date.
#[pyclass(
    name = "MarketDate",
    frozen,
    module = "navlens._native",
    from_py_object
)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct PyMarketDate {
    inner: MarketDate,
}

impl PyMarketDate {
    pub(crate) const fn from_inner(inner: MarketDate) -> Self {
        Self { inner }
    }

    pub(crate) fn into_inner(self) -> MarketDate {
        self.inner
    }
}

#[pymethods]
impl PyMarketDate {
    #[new]
    fn new(year: i32, month: u8, day: u8) -> PyResult<Self> {
        MarketDate::new(year, month, day)
            .map(Self::from_inner)
            .map_err(validation_error)
    }

    fn __str__(&self) -> String {
        self.inner.to_string()
    }

    fn __repr__(&self) -> String {
        format!("MarketDate('{}')", self.inner)
    }
}
