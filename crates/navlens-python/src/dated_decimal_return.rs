use crate::market_date::PyMarketDate;
use navlens_calendar::DatedDecimalReturn;
use pyo3::prelude::*;

/// Python projection of a decimal return ending on one market date.
#[pyclass(
    name = "DatedDecimalReturn",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct PyDatedDecimalReturn {
    inner: DatedDecimalReturn,
}

impl PyDatedDecimalReturn {
    pub(crate) const fn from_inner(inner: DatedDecimalReturn) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyDatedDecimalReturn {
    #[getter]
    const fn date(&self) -> PyMarketDate {
        PyMarketDate::from_inner(self.inner.date())
    }

    #[getter]
    const fn return_decimal(&self) -> f64 {
        self.inner.decimal_return().value()
    }
}
