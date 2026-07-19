use crate::error::validation_error;
use crate::market_date::PyMarketDate;
use crate::utc_timestamp::PyUtcTimestamp;
use navlens_core::FundId;
use navlens_prediction::PredictionRequest;
use pyo3::prelude::*;

/// Python projection of an auditable prediction request.
#[pyclass(
    name = "PredictionRequest",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct PyPredictionRequest {
    inner: PredictionRequest,
}

#[pymethods]
impl PyPredictionRequest {
    #[new]
    fn new(
        fund_id: String,
        prediction_date: PyMarketDate,
        target_date: PyMarketDate,
        generated_at: PyUtcTimestamp,
        data_as_of: PyUtcTimestamp,
    ) -> PyResult<Self> {
        let fund_id = FundId::new(fund_id).map_err(validation_error)?;
        let inner = PredictionRequest::new(
            fund_id,
            prediction_date.into_inner(),
            target_date.into_inner(),
            generated_at.into_inner(),
            data_as_of.into_inner(),
        )
        .map_err(validation_error)?;

        Ok(Self { inner })
    }

    #[getter]
    fn fund_id(&self) -> &str {
        self.inner.fund_id().as_str()
    }

    #[getter]
    const fn prediction_date(&self) -> PyMarketDate {
        PyMarketDate::from_inner(self.inner.prediction_date())
    }

    #[getter]
    const fn target_date(&self) -> PyMarketDate {
        PyMarketDate::from_inner(self.inner.target_date())
    }

    #[getter]
    const fn generated_at(&self) -> PyUtcTimestamp {
        PyUtcTimestamp::from_inner(self.inner.generated_at())
    }

    #[getter]
    const fn data_as_of(&self) -> PyUtcTimestamp {
        PyUtcTimestamp::from_inner(self.inner.data_as_of())
    }
}
