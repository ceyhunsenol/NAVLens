use crate::fx_rate_kind::PyFxRateKind;
use navlens_application::FxReturnPolicy;
use pyo3::prelude::*;

#[pyclass(
    name = "FxReturnPolicy",
    frozen,
    module = "navlens._native",
    eq,
    from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct PyFxReturnPolicy {
    inner: FxReturnPolicy,
}

impl PyFxReturnPolicy {
    pub(crate) const fn into_inner(self) -> FxReturnPolicy {
        self.inner
    }
}

#[allow(clippy::trivially_copy_pass_by_ref)]
#[pymethods]
impl PyFxReturnPolicy {
    #[new]
    fn new(required_fx_rate_kind: PyFxRateKind, max_fx_staleness_calendar_days: u32) -> Self {
        Self {
            inner: FxReturnPolicy::new(
                required_fx_rate_kind.into_inner(),
                max_fx_staleness_calendar_days,
            ),
        }
    }

    #[getter]
    fn required_fx_rate_kind(&self) -> PyFxRateKind {
        PyFxRateKind::from_inner(self.inner.required_fx_rate_kind())
    }

    #[getter]
    fn max_fx_staleness_calendar_days(&self) -> u32 {
        self.inner.max_fx_staleness_calendar_days()
    }
}
