use crate::currency_code::PyCurrencyCode;
use crate::error::validation_error;
use crate::market_date::PyMarketDate;
use crate::price_adjustment::{PyPriceAdjustment, price_adjustment_name};
use crate::unit_price::PyUnitPrice;
use navlens_calendar::SecurityPriceObservation;
use navlens_core::InstrumentId;
use pyo3::prelude::*;

/// Python projection of a security price observation.
#[pyclass(
    name = "SecurityPriceObservation",
    frozen,
    module = "navlens._native",
    eq,
    from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PySecurityPriceObservation {
    inner: SecurityPriceObservation,
}

impl PySecurityPriceObservation {
    pub(crate) const fn from_inner(inner: SecurityPriceObservation) -> Self {
        Self { inner }
    }

    pub(crate) fn into_inner(self) -> SecurityPriceObservation {
        self.inner
    }
}

#[pymethods]
impl PySecurityPriceObservation {
    #[new]
    fn new(
        instrument_id: &str,
        market_date: PyMarketDate,
        price: PyUnitPrice,
        currency: PyCurrencyCode,
        adjustment: PyPriceAdjustment,
    ) -> PyResult<Self> {
        let inst_id = InstrumentId::new(instrument_id).map_err(validation_error)?;
        let inner = SecurityPriceObservation::new(
            inst_id,
            market_date.into_inner(),
            price.into_inner(),
            currency.into_inner(),
            adjustment.into_inner(),
        );
        Ok(Self { inner })
    }

    #[getter]
    fn instrument_id(&self) -> &str {
        self.inner.instrument_id().as_str()
    }

    #[getter]
    const fn market_date(&self) -> PyMarketDate {
        PyMarketDate::from_inner(self.inner.market_date())
    }

    #[getter]
    const fn price(&self) -> PyUnitPrice {
        PyUnitPrice::from_inner(self.inner.price())
    }

    #[getter]
    fn currency(&self) -> PyCurrencyCode {
        PyCurrencyCode::from_inner(self.inner.currency().clone())
    }

    #[getter]
    const fn adjustment(&self) -> PyPriceAdjustment {
        PyPriceAdjustment::from_inner(self.inner.adjustment())
    }

    fn __repr__(&self) -> String {
        format!(
            "SecurityPriceObservation(instrument_id='{}', market_date={}, price={}, currency='{}', adjustment='{}')",
            self.inner.instrument_id(),
            self.inner.market_date(),
            self.inner.price().value(),
            self.inner.currency().as_str(),
            price_adjustment_name(self.inner.adjustment())
        )
    }
}
