use crate::error::validation_error;
use crate::market_date::PyMarketDate;
use crate::return_prediction::PyReturnPrediction;
use navlens_backtest::Observation;
use navlens_core::DecimalReturn;
use pyo3::prelude::*;

/// Python input mapping for one dated backtest observation.
#[pyclass(
    name = "BacktestObservation",
    frozen,
    module = "navlens._native",
    from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyBacktestObservation {
    inner: Observation,
}

impl PyBacktestObservation {
    pub(crate) const fn into_inner(self) -> Observation {
        self.inner
    }
}

#[pymethods]
impl PyBacktestObservation {
    #[new]
    fn new(
        prediction_date: PyMarketDate,
        target_date: PyMarketDate,
        prediction: PyReturnPrediction,
        actual_return: f64,
    ) -> PyResult<Self> {
        let prediction = prediction.into_inner();
        let actual_return = DecimalReturn::new(actual_return).map_err(validation_error)?;
        let observation = Observation::new(
            prediction_date.into_inner(),
            target_date.into_inner(),
            prediction.expected_return(),
            actual_return,
        )
        .map_err(validation_error)?
        .with_prediction_interval(prediction.interval());

        Ok(Self { inner: observation })
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
    const fn predicted_return(&self) -> f64 {
        self.inner.predicted_return().value()
    }

    #[getter]
    const fn actual_return(&self) -> f64 {
        self.inner.actual_return().value()
    }
}
