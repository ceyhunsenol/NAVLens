use crate::error::validation_error;
use crate::model_descriptor::PyModelDescriptor;
use navlens_core::{ConfidenceLevel, DecimalReturn, PredictionInterval};
use navlens_prediction::{ModelDescriptor, ReturnPrediction};
use pyo3::prelude::*;

/// Python projection of a validated return prediction.
#[pyclass(
    name = "ReturnPrediction",
    frozen,
    module = "navlens._native",
    from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyReturnPrediction {
    inner: ReturnPrediction,
}

#[pyfunction]
pub(crate) fn create_return_prediction(
    expected_return: f64,
    lower_bound: f64,
    upper_bound: f64,
    confidence_level: f64,
    model: PyModelDescriptor,
) -> PyResult<PyReturnPrediction> {
    build_return_prediction(
        expected_return,
        lower_bound,
        upper_bound,
        confidence_level,
        model.into_inner(),
    )
    .map(|inner| PyReturnPrediction { inner })
    .map_err(validation_error)
}

fn build_return_prediction(
    expected_return: f64,
    lower_bound: f64,
    upper_bound: f64,
    confidence_level: f64,
    model: ModelDescriptor,
) -> Result<ReturnPrediction, Box<dyn std::error::Error>> {
    let expected_return = DecimalReturn::new(expected_return)?;
    let lower_bound = DecimalReturn::new(lower_bound)?;
    let upper_bound = DecimalReturn::new(upper_bound)?;
    let confidence_level = ConfidenceLevel::new(confidence_level)?;
    let interval = PredictionInterval::new(lower_bound, upper_bound, confidence_level)?;

    Ok(ReturnPrediction::new(expected_return, interval, model)?)
}

impl PyReturnPrediction {
    pub(crate) fn into_inner(self) -> ReturnPrediction {
        self.inner
    }
}

#[pymethods]
impl PyReturnPrediction {
    #[getter]
    const fn expected_return(&self) -> f64 {
        self.inner.expected_return().value()
    }

    #[getter]
    const fn lower_bound(&self) -> f64 {
        self.inner.interval().lower().value()
    }

    #[getter]
    const fn upper_bound(&self) -> f64 {
        self.inner.interval().upper().value()
    }

    #[getter]
    const fn confidence_level(&self) -> f64 {
        self.inner.interval().confidence_level().value()
    }

    #[getter]
    fn model(&self) -> PyModelDescriptor {
        PyModelDescriptor::from_inner(self.inner.model().clone())
    }
}

#[cfg(test)]
mod tests {
    use super::build_return_prediction;
    use navlens_core::DecimalReturn;
    use navlens_prediction::ModelDescriptor;

    #[test]
    fn delegates_validation_to_domain_types() {
        let model = ModelDescriptor::new("ridge", "0.1.0", "market-v1")
            .expect("test metadata must be valid");
        let result = build_return_prediction(0.01, -0.02, 0.03, 0.9, model)
            .expect("test prediction must be valid");

        assert_eq!(
            result.expected_return(),
            DecimalReturn::new(0.01).expect("test return must be valid")
        );
    }

    #[test]
    fn rejects_expected_return_outside_interval() {
        let model = ModelDescriptor::new("ridge", "0.1.0", "market-v1")
            .expect("test metadata must be valid");

        assert!(build_return_prediction(0.04, -0.02, 0.03, 0.9, model).is_err());
    }
}
