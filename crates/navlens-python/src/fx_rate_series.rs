use crate::currency_pair::PyCurrencyPair;
use crate::error::validation_error;
use crate::fx_rate_kind::{PyFxRateKind, fx_rate_kind_name};
use crate::fx_rate_observation::PyFxRateObservation;
use navlens_calendar::FxRateSeries;
use pyo3::prelude::*;

/// Python projection of a validated chronological FX rate series.
#[pyclass(
    name = "FxRateSeries",
    frozen,
    module = "navlens._native",
    eq,
    from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyFxRateSeries {
    inner: FxRateSeries,
}

impl PyFxRateSeries {
    pub(crate) fn from_inner(inner: FxRateSeries) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyFxRateSeries {
    #[new]
    fn new(observations: Vec<PyFxRateObservation>) -> PyResult<Self> {
        let rust_observations = observations
            .into_iter()
            .map(PyFxRateObservation::into_inner)
            .collect();
        FxRateSeries::new(rust_observations)
            .map(Self::from_inner)
            .map_err(validation_error)
    }

    #[getter]
    fn pair(&self) -> PyCurrencyPair {
        PyCurrencyPair::from_inner(self.inner.pair().clone())
    }

    #[getter]
    fn kind(&self) -> PyFxRateKind {
        PyFxRateKind::from_inner(self.inner.kind())
    }

    #[getter]
    fn observations(&self) -> Vec<PyFxRateObservation> {
        self.inner
            .observations()
            .iter()
            .cloned()
            .map(PyFxRateObservation::from_inner)
            .collect()
    }

    fn __len__(&self) -> usize {
        self.inner.observations().len()
    }

    fn __repr__(&self) -> String {
        format!(
            "FxRateSeries(base_currency='{}', quote_currency='{}', kind='{}', observations_count={})",
            self.inner.pair().base_currency().as_str(),
            self.inner.pair().quote_currency().as_str(),
            fx_rate_kind_name(self.inner.kind()),
            self.inner.observations().len()
        )
    }
}
