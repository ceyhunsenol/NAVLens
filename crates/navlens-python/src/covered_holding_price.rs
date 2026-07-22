use crate::holding_position::PyHoldingPosition;
use crate::security_price_series::PySecurityPriceSeries;
use navlens_application::CoveredHoldingPrice;
use pyo3::prelude::*;

#[pyclass(
    name = "CoveredHoldingPrice",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone)]
pub(crate) struct PyCoveredHoldingPrice {
    inner: CoveredHoldingPrice,
}

impl PyCoveredHoldingPrice {
    pub(crate) const fn from_inner(inner: CoveredHoldingPrice) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyCoveredHoldingPrice {
    #[getter]
    fn holding(&self) -> PyHoldingPosition {
        PyHoldingPosition::from_inner(self.inner.holding().clone())
    }

    #[getter]
    fn series(&self) -> PySecurityPriceSeries {
        PySecurityPriceSeries::from_inner(self.inner.series().clone())
    }
}
