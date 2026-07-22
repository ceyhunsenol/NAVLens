use crate::currency_code::PyCurrencyCode;
use crate::error::validation_error;
use crate::price_adjustment::PyPriceAdjustment;
use crate::security_price_observation::PySecurityPriceObservation;
use navlens_calendar::SecurityPriceSeries;
use pyo3::prelude::*;

/// Python projection of a validated chronological security price series.
#[pyclass(
    name = "SecurityPriceSeries",
    frozen,
    module = "navlens._native",
    eq,
    from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PySecurityPriceSeries {
    inner: SecurityPriceSeries,
}

impl PySecurityPriceSeries {
    pub(crate) fn from_inner(inner: SecurityPriceSeries) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PySecurityPriceSeries {
    #[new]
    fn new(observations: Vec<PySecurityPriceObservation>) -> PyResult<Self> {
        let rust_observations = observations
            .into_iter()
            .map(PySecurityPriceObservation::into_inner)
            .collect();
        SecurityPriceSeries::new(rust_observations)
            .map(Self::from_inner)
            .map_err(validation_error)
    }

    #[getter]
    fn instrument_id(&self) -> &str {
        self.inner.instrument_id().as_str()
    }

    #[getter]
    fn currency(&self) -> PyCurrencyCode {
        PyCurrencyCode::from_inner(self.inner.currency().clone())
    }

    #[getter]
    fn adjustment(&self) -> PyPriceAdjustment {
        PyPriceAdjustment::from_inner(self.inner.adjustment())
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

    fn __len__(&self) -> usize {
        self.inner.observations().len()
    }

    fn __repr__(&self) -> String {
        format!(
            "SecurityPriceSeries(instrument_id='{}', observations_count={})",
            self.inner.instrument_id(),
            self.inner.observations().len()
        )
    }
}
