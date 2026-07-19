use navlens_prediction::UtcTimestamp;
use pyo3::prelude::*;

/// Python projection of a UTC instant expressed in Unix seconds.
#[pyclass(
    name = "UtcTimestamp",
    frozen,
    module = "navlens._native",
    from_py_object
)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct PyUtcTimestamp {
    inner: UtcTimestamp,
}

impl PyUtcTimestamp {
    pub(crate) const fn from_inner(inner: UtcTimestamp) -> Self {
        Self { inner }
    }

    pub(crate) fn into_inner(self) -> UtcTimestamp {
        self.inner
    }
}

#[pymethods]
impl PyUtcTimestamp {
    #[new]
    const fn new(unix_seconds: i64) -> Self {
        Self::from_inner(UtcTimestamp::from_unix_seconds(unix_seconds))
    }

    #[getter]
    const fn unix_seconds(&self) -> i64 {
        self.inner.unix_seconds()
    }

    fn __repr__(&self) -> String {
        format!("UtcTimestamp(unix_seconds={})", self.inner.unix_seconds())
    }
}
