use navlens_application::ReturnCoverageGapReason;
use pyo3::prelude::*;

/// Python projection of the reason why a covered holding could not provide a return.
#[pyclass(
    name = "ReturnCoverageGapReason",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyReturnCoverageGapReason {
    inner: ReturnCoverageGapReason,
}

impl PyReturnCoverageGapReason {
    pub(crate) const fn from_inner(inner: ReturnCoverageGapReason) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyReturnCoverageGapReason {
    #[getter]
    fn kind(&self) -> &'static str {
        match &self.inner {
            ReturnCoverageGapReason::MissingExactPeriodReturn => "missing_exact_period_return",
            ReturnCoverageGapReason::MissingDirectFxCandidate { .. } => {
                "missing_direct_fx_candidate"
            }
            ReturnCoverageGapReason::FxRateKindMismatch { .. } => "fx_rate_kind_mismatch",
            ReturnCoverageGapReason::MissingFxStartObservation { .. } => {
                "missing_fx_start_observation"
            }
            ReturnCoverageGapReason::StaleFxStartObservation { .. } => "stale_fx_start_observation",
            ReturnCoverageGapReason::MissingFxEndObservation { .. } => "missing_fx_end_observation",
            ReturnCoverageGapReason::StaleFxEndObservation { .. } => "stale_fx_end_observation",
        }
    }

    fn __repr__(&self) -> String {
        format!("ReturnCoverageGapReason(kind='{}')", self.kind())
    }
}
