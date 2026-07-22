use crate::security_price_observation::PySecurityPriceObservation;
use navlens_application::SecurityPriceHistoryCandidate;
use navlens_core::InstrumentId;
use pyo3::prelude::*;

#[pyclass(
    name = "SecurityPriceHistoryCandidate",
    frozen,
    module = "navlens._native",
    from_py_object
)]
#[derive(Clone)]
pub(crate) struct PySecurityPriceHistoryCandidate {
    inner: SecurityPriceHistoryCandidate,
}

impl PySecurityPriceHistoryCandidate {
    pub(crate) const fn from_inner(inner: SecurityPriceHistoryCandidate) -> Self {
        Self { inner }
    }

    pub(crate) fn into_inner(self) -> SecurityPriceHistoryCandidate {
        self.inner
    }
}

#[allow(clippy::needless_pass_by_value)]
#[pymethods]
impl PySecurityPriceHistoryCandidate {
    #[new]
    fn new(instrument_id: &str, observations: Vec<PySecurityPriceObservation>) -> PyResult<Self> {
        let inst_id = InstrumentId::new(instrument_id).map_err(crate::error::validation_error)?;
        let domain_observations = observations
            .into_iter()
            .map(PySecurityPriceObservation::into_inner)
            .collect();

        let candidate = SecurityPriceHistoryCandidate::new(inst_id, domain_observations)
            .map_err(crate::error::validation_error)?;

        Ok(Self::from_inner(candidate))
    }

    #[getter]
    fn instrument_id(&self) -> String {
        self.inner.instrument_id().to_string()
    }

    #[getter]
    fn observations(&self) -> Vec<PySecurityPriceObservation> {
        self.inner
            .observations()
            .iter()
            .cloned()
            .map(PySecurityPriceObservation::from_inner)
            .collect()
    }
}
