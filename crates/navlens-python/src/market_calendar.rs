use crate::error::validation_error;
use crate::market_date::PyMarketDate;
use crate::session_kind::PySessionKind;
use crate::session_override::PySessionOverride;
use navlens_calendar::MarketCalendar;
use pyo3::prelude::*;

/// Python projection of a deterministic market calendar.
#[pyclass(
    name = "MarketCalendar",
    frozen,
    module = "navlens._native",
    eq,
    from_py_object
)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct PyMarketCalendar {
    inner: MarketCalendar,
}

impl PyMarketCalendar {
    pub(crate) const fn from_inner(inner: MarketCalendar) -> Self {
        Self { inner }
    }
}

#[allow(clippy::trivially_copy_pass_by_ref)]
#[pymethods]
impl PyMarketCalendar {
    #[new]
    #[pyo3(signature = (overrides=None))]
    fn new(overrides: Option<Vec<PySessionOverride>>) -> PyResult<Self> {
        let rust_overrides: Vec<_> = overrides
            .unwrap_or_default()
            .into_iter()
            .map(PySessionOverride::into_inner)
            .collect();

        MarketCalendar::new(&rust_overrides)
            .map(Self::from_inner)
            .map_err(validation_error)
    }

    fn session_on(&self, date: PyMarketDate) -> PySessionKind {
        PySessionKind::from_inner(self.inner.session_on(date.into_inner()))
    }

    fn next_open_date(&self, date: PyMarketDate) -> PyResult<PyMarketDate> {
        self.inner
            .next_open_date(date.into_inner())
            .map(PyMarketDate::from_inner)
            .map_err(validation_error)
    }
}
