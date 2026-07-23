use crate::error::validation_error;
use crate::market_date::PyMarketDate;
use crate::return_period::PyReturnPeriod;
use navlens_calendar::PeriodDecimalReturn;
use navlens_core::DecimalReturn;
use pyo3::prelude::*;

/// Python projection of a decimal return computed over an exact market return period.
#[pyclass(
    name = "PeriodDecimalReturn",
    frozen,
    module = "navlens._native",
    eq,
    from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct PyPeriodDecimalReturn {
    inner: PeriodDecimalReturn,
}

impl PyPeriodDecimalReturn {
    pub(crate) const fn from_inner(inner: PeriodDecimalReturn) -> Self {
        Self { inner }
    }

    pub(crate) const fn into_inner(self) -> PeriodDecimalReturn {
        self.inner
    }
}

#[allow(clippy::trivially_copy_pass_by_ref)]
#[pymethods]
impl PyPeriodDecimalReturn {
    #[new]
    fn new(period: PyReturnPeriod, return_decimal: f64) -> PyResult<Self> {
        let decimal_return = DecimalReturn::new(return_decimal).map_err(validation_error)?;
        let inner = PeriodDecimalReturn::from_period(period.into_inner(), decimal_return);
        Ok(Self::from_inner(inner))
    }

    #[getter]
    const fn period(&self) -> PyReturnPeriod {
        PyReturnPeriod::from_inner(self.inner.period())
    }

    #[getter]
    const fn period_start_date(&self) -> PyMarketDate {
        PyMarketDate::from_inner(self.inner.period_start_date())
    }

    #[getter]
    const fn period_end_date(&self) -> PyMarketDate {
        PyMarketDate::from_inner(self.inner.period_end_date())
    }

    #[getter]
    const fn return_decimal(&self) -> f64 {
        self.inner.decimal_return().value()
    }

    fn __repr__(&self) -> String {
        format!(
            "PeriodDecimalReturn(period=ReturnPeriod(period_start_date=MarketDate('{}'), period_end_date=MarketDate('{}')), return_decimal={})",
            self.inner.period_start_date(),
            self.inner.period_end_date(),
            self.inner.decimal_return().value()
        )
    }
}
