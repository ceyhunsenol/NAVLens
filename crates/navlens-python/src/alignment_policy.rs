use crate::currency_code::PyCurrencyCode;
use crate::market_date::PyMarketDate;
use crate::price_adjustment::PyPriceAdjustment;
use navlens_application::AlignmentPolicy;
use pyo3::prelude::*;

#[pyclass(
    name = "AlignmentPolicy",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone)]
pub(crate) struct PyAlignmentPolicy {
    inner: AlignmentPolicy,
}

impl PyAlignmentPolicy {
    pub(crate) const fn from_inner(inner: AlignmentPolicy) -> Self {
        Self { inner }
    }

    pub(crate) fn clone_inner(&self) -> AlignmentPolicy {
        self.inner.clone()
    }
}

#[pymethods]
impl PyAlignmentPolicy {
    #[new]
    fn new(
        fund_base_currency: PyCurrencyCode,
        required_price_adjustment: PyPriceAdjustment,
        pricing_as_of_date: PyMarketDate,
        minimum_observations: usize,
        max_staleness_calendar_days: u32,
    ) -> PyResult<Self> {
        let policy = AlignmentPolicy::new(
            fund_base_currency.into_inner(),
            required_price_adjustment.into_inner(),
            pricing_as_of_date.into_inner(),
            minimum_observations,
            max_staleness_calendar_days,
        )
        .map_err(crate::error::validation_error)?;

        Ok(Self { inner: policy })
    }

    #[getter]
    fn fund_base_currency(&self) -> PyCurrencyCode {
        PyCurrencyCode::from_inner(self.inner.fund_base_currency().clone())
    }

    #[getter]
    fn required_price_adjustment(&self) -> PyPriceAdjustment {
        PyPriceAdjustment::from_inner(self.inner.required_price_adjustment())
    }

    #[getter]
    fn pricing_as_of_date(&self) -> PyMarketDate {
        PyMarketDate::from_inner(self.inner.pricing_as_of_date())
    }

    #[getter]
    fn minimum_observations(&self) -> usize {
        self.inner.minimum_observations()
    }

    #[getter]
    fn max_staleness_calendar_days(&self) -> u32 {
        self.inner.max_staleness_calendar_days()
    }
}
