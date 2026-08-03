use crate::market_date::PyMarketDate;
use crate::session_kind::{PySessionKind, session_kind_name};
use navlens_calendar::SessionOverride;
use pyo3::prelude::*;

/// Python projection of an authoritative session override for a market date.
#[pyclass(
    name = "SessionOverride",
    frozen,
    module = "navlens._native",
    eq,
    from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct PySessionOverride {
    inner: SessionOverride,
}

impl PySessionOverride {
    pub(crate) const fn into_inner(self) -> SessionOverride {
        self.inner
    }
}

#[allow(clippy::trivially_copy_pass_by_ref)]
#[pymethods]
impl PySessionOverride {
    #[new]
    fn new(date: PyMarketDate, session: PySessionKind) -> Self {
        Self {
            inner: SessionOverride::new(date.into_inner(), session.into_inner()),
        }
    }

    #[getter]
    const fn date(&self) -> PyMarketDate {
        PyMarketDate::from_inner(self.inner.date())
    }

    #[getter]
    const fn session(&self) -> PySessionKind {
        PySessionKind::from_inner(self.inner.session())
    }

    fn __repr__(&self) -> String {
        format!(
            "SessionOverride(date=MarketDate('{}'), session=SessionKind('{}'))",
            self.inner.date(),
            session_kind_name(self.inner.session())
        )
    }

    fn __str__(&self) -> String {
        format!(
            "{}: {}",
            self.inner.date(),
            session_kind_name(self.inner.session())
        )
    }
}
