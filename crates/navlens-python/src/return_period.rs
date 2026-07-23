use crate::error::validation_error;
use crate::market_date::PyMarketDate;
use navlens_calendar::ReturnPeriod;
use pyo3::prelude::*;

/// Python projection of a validated market return observation period.
#[pyclass(
    name = "ReturnPeriod",
    frozen,
    module = "navlens._native",
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub(crate) struct PyReturnPeriod {
    inner: ReturnPeriod,
}

impl PyReturnPeriod {
    pub(crate) const fn from_inner(inner: ReturnPeriod) -> Self {
        Self { inner }
    }

    pub(crate) const fn into_inner(self) -> ReturnPeriod {
        self.inner
    }
}

#[allow(clippy::trivially_copy_pass_by_ref)]
#[pymethods]
impl PyReturnPeriod {
    #[new]
    fn new(period_start_date: PyMarketDate, period_end_date: PyMarketDate) -> PyResult<Self> {
        ReturnPeriod::new(period_start_date.into_inner(), period_end_date.into_inner())
            .map(Self::from_inner)
            .map_err(validation_error)
    }

    #[getter]
    const fn period_start_date(&self) -> PyMarketDate {
        PyMarketDate::from_inner(self.inner.period_start_date())
    }

    #[getter]
    const fn period_end_date(&self) -> PyMarketDate {
        PyMarketDate::from_inner(self.inner.period_end_date())
    }

    fn __repr__(&self) -> String {
        format!(
            "ReturnPeriod(period_start_date=MarketDate('{}'), period_end_date=MarketDate('{}'))",
            self.inner.period_start_date(),
            self.inner.period_end_date()
        )
    }
}
