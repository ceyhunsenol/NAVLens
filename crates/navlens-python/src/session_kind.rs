use crate::error::validation_error;
use navlens_calendar::SessionKind;
use pyo3::prelude::*;

/// Python projection of a trading or valuation availability session kind.
#[pyclass(
    name = "SessionKind",
    frozen,
    module = "navlens._native",
    eq,
    from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct PySessionKind {
    inner: SessionKind,
}

impl PySessionKind {
    pub(crate) const fn from_inner(inner: SessionKind) -> Self {
        Self { inner }
    }

    pub(crate) const fn into_inner(self) -> SessionKind {
        self.inner
    }
}

pub(crate) fn parse_session_kind(value: &str) -> Result<SessionKind, String> {
    match value.to_ascii_lowercase().as_str() {
        "full_day" => Ok(SessionKind::FullDay),
        "half_day" => Ok(SessionKind::HalfDay),
        "closed" => Ok(SessionKind::Closed),
        _ => Err(format!(
            "unknown session kind '{value}'; expected one of: full_day, half_day, closed"
        )),
    }
}

pub(crate) fn session_kind_name(kind: SessionKind) -> &'static str {
    match kind {
        SessionKind::FullDay => "full_day",
        SessionKind::HalfDay => "half_day",
        SessionKind::Closed => "closed",
    }
}

#[allow(clippy::trivially_copy_pass_by_ref)]
#[pymethods]
impl PySessionKind {
    #[new]
    fn new(value: &str) -> PyResult<Self> {
        parse_session_kind(value)
            .map(Self::from_inner)
            .map_err(validation_error)
    }

    #[getter]
    fn name(&self) -> &'static str {
        session_kind_name(self.inner)
    }

    const fn is_open(&self) -> bool {
        self.inner.is_open()
    }

    fn __repr__(&self) -> String {
        format!("SessionKind('{}')", session_kind_name(self.inner))
    }

    fn __str__(&self) -> &'static str {
        session_kind_name(self.inner)
    }
}
