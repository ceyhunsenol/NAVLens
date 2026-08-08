use crate::fx_rate_observation::PyFxRateObservation;
use crate::market_date::PyMarketDate;
use navlens_application::FxBoundaryEvidence;
use pyo3::prelude::*;

#[pyclass(
    name = "FxBoundaryEvidence",
    frozen,
    module = "navlens._native",
    eq,
    from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyFxBoundaryEvidence {
    inner: FxBoundaryEvidence,
}

impl PyFxBoundaryEvidence {
    pub(crate) const fn from_inner(inner: FxBoundaryEvidence) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyFxBoundaryEvidence {
    #[getter]
    fn requested_date(&self) -> PyMarketDate {
        PyMarketDate::from_inner(self.inner.requested_date())
    }

    #[getter]
    fn observation(&self) -> PyFxRateObservation {
        PyFxRateObservation::from_inner(self.inner.observation().clone())
    }

    #[getter]
    fn staleness_calendar_days(&self) -> u32 {
        self.inner.staleness_calendar_days()
    }
}
