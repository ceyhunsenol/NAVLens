use crate::currency_pair::PyCurrencyPair;
use crate::fx_rate::PyFxRate;
use crate::fx_rate_kind::{PyFxRateKind, fx_rate_kind_name};
use crate::market_date::PyMarketDate;
use navlens_calendar::FxRateObservation;
use pyo3::prelude::*;

/// Python projection of an FX rate observation.
#[pyclass(
    name = "FxRateObservation",
    frozen,
    module = "navlens._native",
    eq,
    from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyFxRateObservation {
    inner: FxRateObservation,
}

impl PyFxRateObservation {
    pub(crate) const fn from_inner(inner: FxRateObservation) -> Self {
        Self { inner }
    }

    pub(crate) fn into_inner(self) -> FxRateObservation {
        self.inner
    }
}

#[pymethods]
impl PyFxRateObservation {
    #[new]
    fn new(
        pair: PyCurrencyPair,
        market_date: PyMarketDate,
        rate: PyFxRate,
        kind: PyFxRateKind,
    ) -> Self {
        let inner = FxRateObservation::new(
            pair.into_inner(),
            market_date.into_inner(),
            rate.into_inner(),
            kind.into_inner(),
        );
        Self { inner }
    }

    #[getter]
    fn pair(&self) -> PyCurrencyPair {
        PyCurrencyPair::from_inner(self.inner.pair().clone())
    }

    #[getter]
    const fn market_date(&self) -> PyMarketDate {
        PyMarketDate::from_inner(self.inner.market_date())
    }

    #[getter]
    const fn rate(&self) -> PyFxRate {
        PyFxRate::from_inner(self.inner.rate())
    }

    #[getter]
    const fn kind(&self) -> PyFxRateKind {
        PyFxRateKind::from_inner(self.inner.kind())
    }

    fn __repr__(&self) -> String {
        format!(
            "FxRateObservation(pair=CurrencyPair(base_currency=CurrencyCode('{}'), quote_currency=CurrencyCode('{}')), market_date={}, rate={}, kind='{}')",
            self.inner.pair().base_currency().as_str(),
            self.inner.pair().quote_currency().as_str(),
            self.inner.market_date(),
            self.inner.rate().quote_currency_per_one_base_currency(),
            fx_rate_kind_name(self.inner.kind())
        )
    }
}
