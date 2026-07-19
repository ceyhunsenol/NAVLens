use crate::market_date::PyMarketDate;
use crate::unit_price::PyUnitPrice;
use navlens_calendar::PriceObservation;
use pyo3::prelude::*;

/// Python projection of one dated unit price.
#[pyclass(
    name = "PriceObservation",
    frozen,
    module = "navlens._native",
    from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct PyPriceObservation {
    inner: PriceObservation,
}

impl PyPriceObservation {
    pub(crate) const fn into_inner(self) -> PriceObservation {
        self.inner
    }
}

#[pymethods]
impl PyPriceObservation {
    #[new]
    fn new(date: PyMarketDate, unit_price: PyUnitPrice) -> Self {
        Self {
            inner: PriceObservation::new(date.into_inner(), unit_price.into_inner()),
        }
    }

    #[getter]
    const fn date(&self) -> PyMarketDate {
        PyMarketDate::from_inner(self.inner.date())
    }

    #[getter]
    const fn unit_price(&self) -> PyUnitPrice {
        PyUnitPrice::from_inner(self.inner.unit_price())
    }
}
