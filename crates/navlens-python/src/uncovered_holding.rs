use crate::coverage_gap_reason::PyCoverageGapReason;
use crate::holding_position::PyHoldingPosition;
use navlens_application::UncoveredHolding;
use pyo3::prelude::*;

#[pyclass(
    name = "UncoveredHolding",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone)]
pub(crate) struct PyUncoveredHolding {
    inner: UncoveredHolding,
}

impl PyUncoveredHolding {
    pub(crate) const fn from_inner(inner: UncoveredHolding) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyUncoveredHolding {
    #[getter]
    fn holding(&self) -> PyHoldingPosition {
        PyHoldingPosition::from_inner(self.inner.holding().clone())
    }

    #[getter]
    fn reason(&self) -> PyCoverageGapReason {
        PyCoverageGapReason::from_inner(self.inner.reason().clone())
    }
}
