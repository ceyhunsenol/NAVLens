use crate::holding_position::PyHoldingPosition;
use crate::return_coverage_gap_reason::PyReturnCoverageGapReason;
use navlens_application::ReturnCoverageGap;
use pyo3::prelude::*;

/// Python projection of a holding that had price coverage but failed to provide an exact period return.
#[pyclass(
    name = "ReturnCoverageGap",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyReturnCoverageGap {
    inner: ReturnCoverageGap,
}

impl PyReturnCoverageGap {
    pub(crate) fn from_inner(inner: ReturnCoverageGap) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyReturnCoverageGap {
    #[getter]
    fn holding(&self) -> PyHoldingPosition {
        PyHoldingPosition::from_inner(self.inner.holding().clone())
    }

    #[getter]
    fn reason(&self) -> PyReturnCoverageGapReason {
        PyReturnCoverageGapReason::from_inner(self.inner.reason().clone())
    }
}
