use crate::asset_class::PyAssetClass;
use crate::currency_code::PyCurrencyCode;
use crate::market_date::PyMarketDate;
use crate::price_adjustment::PyPriceAdjustment;
use navlens_application::CoverageGapReason;
use pyo3::prelude::*;

#[pyclass(
    name = "CoverageGapReason",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone)]
pub(crate) struct PyCoverageGapReason {
    inner: CoverageGapReason,
}

impl PyCoverageGapReason {
    pub(crate) const fn from_inner(inner: CoverageGapReason) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyCoverageGapReason {
    #[getter]
    fn kind(&self) -> &'static str {
        match &self.inner {
            CoverageGapReason::UnsupportedAssetClass { .. } => "unsupported_asset_class",
            CoverageGapReason::MissingPriceSeries => "missing_price_series",
            CoverageGapReason::InsufficientObservations { .. } => "insufficient_observations",
            CoverageGapReason::CurrencyMismatch { .. } => "currency_mismatch",
            CoverageGapReason::IncompatiblePriceAdjustment { .. } => {
                "incompatible_price_adjustment"
            }
            CoverageGapReason::StalePrices { .. } => "stale_prices",
        }
    }

    #[getter]
    fn asset_class(&self) -> Option<PyAssetClass> {
        match &self.inner {
            CoverageGapReason::UnsupportedAssetClass { asset_class } => {
                Some(PyAssetClass::from_inner(*asset_class))
            }
            _ => None,
        }
    }

    #[getter]
    fn observations_found(&self) -> Option<usize> {
        match &self.inner {
            CoverageGapReason::InsufficientObservations { found, .. } => Some(*found),
            _ => None,
        }
    }

    #[getter]
    fn observations_required(&self) -> Option<usize> {
        match &self.inner {
            CoverageGapReason::InsufficientObservations { required, .. } => Some(*required),
            _ => None,
        }
    }

    #[getter]
    fn expected_currency(&self) -> Option<PyCurrencyCode> {
        match &self.inner {
            CoverageGapReason::CurrencyMismatch { expected, .. } => {
                Some(PyCurrencyCode::from_inner(expected.clone()))
            }
            _ => None,
        }
    }

    #[getter]
    fn found_currency(&self) -> Option<PyCurrencyCode> {
        match &self.inner {
            CoverageGapReason::CurrencyMismatch { found, .. } => {
                Some(PyCurrencyCode::from_inner(found.clone()))
            }
            _ => None,
        }
    }

    #[getter]
    fn expected_price_adjustment(&self) -> Option<PyPriceAdjustment> {
        match &self.inner {
            CoverageGapReason::IncompatiblePriceAdjustment { expected, .. } => {
                Some(PyPriceAdjustment::from_inner(*expected))
            }
            _ => None,
        }
    }

    #[getter]
    fn found_price_adjustment(&self) -> Option<PyPriceAdjustment> {
        match &self.inner {
            CoverageGapReason::IncompatiblePriceAdjustment { found, .. } => {
                Some(PyPriceAdjustment::from_inner(*found))
            }
            _ => None,
        }
    }

    #[getter]
    fn latest_observation_date(&self) -> Option<PyMarketDate> {
        match &self.inner {
            CoverageGapReason::StalePrices {
                latest_observation_date,
                ..
            } => Some(PyMarketDate::from_inner(*latest_observation_date)),
            _ => None,
        }
    }

    #[getter]
    fn pricing_as_of_date(&self) -> Option<PyMarketDate> {
        match &self.inner {
            CoverageGapReason::StalePrices {
                pricing_as_of_date, ..
            } => Some(PyMarketDate::from_inner(*pricing_as_of_date)),
            _ => None,
        }
    }

    #[getter]
    fn max_staleness_calendar_days(&self) -> Option<u32> {
        match &self.inner {
            CoverageGapReason::StalePrices {
                max_staleness_calendar_days,
                ..
            } => Some(*max_staleness_calendar_days),
            _ => None,
        }
    }
}
