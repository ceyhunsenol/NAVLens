use crate::asset_class::PyAssetClass;
use crate::error::validation_error;
use navlens_core::{HoldingPosition, InstrumentId, PortfolioWeight};
use pyo3::prelude::*;

/// Python projection of a single instrument exposure in a fund composition.
#[pyclass(
    name = "HoldingPosition",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyHoldingPosition {
    inner: HoldingPosition,
}

#[pymethods]
impl PyHoldingPosition {
    #[new]
    fn new(instrument_id: &str, asset_class: PyAssetClass, weight: f64) -> PyResult<Self> {
        build_holding_position(instrument_id, asset_class, weight).map_err(validation_error)
    }

    #[getter]
    fn instrument_id(&self) -> &str {
        self.inner.instrument_id().as_str()
    }

    #[getter]
    fn asset_class(&self) -> PyAssetClass {
        PyAssetClass::from_inner(self.inner.asset_class())
    }

    #[getter]
    fn fund_total_weight(&self) -> f64 {
        self.inner.fund_total_weight().value()
    }

    fn __repr__(&self) -> String {
        format!(
            "HoldingPosition(instrument_id='{}', asset_class='{}', weight={})",
            self.inner.instrument_id(),
            super::asset_class::asset_class_name(self.inner.asset_class()),
            self.inner.fund_total_weight().value(),
        )
    }
}

fn build_holding_position(
    instrument_id: &str,
    asset_class: PyAssetClass,
    weight: f64,
) -> Result<PyHoldingPosition, Box<dyn std::error::Error>> {
    let instrument_id = InstrumentId::new(instrument_id)?;
    let weight = PortfolioWeight::new(weight)?;
    let position = HoldingPosition::new(instrument_id, asset_class.into_inner(), weight);
    Ok(PyHoldingPosition { inner: position })
}
