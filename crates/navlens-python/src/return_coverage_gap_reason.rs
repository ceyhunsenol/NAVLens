use crate::currency_pair::PyCurrencyPair;
use crate::fx_boundary_evidence::PyFxBoundaryEvidence;
use crate::fx_rate_kind::PyFxRateKind;
use crate::market_date::PyMarketDate;
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
            ReturnCoverageGapReason::StaleFxEndObservation { .. } => "stale_fx_end_observation",
        }
    }

    #[getter]
    fn required_pair(&self) -> Option<PyCurrencyPair> {
        match &self.inner {
            ReturnCoverageGapReason::MissingDirectFxCandidate { required_pair, .. }
            | ReturnCoverageGapReason::FxRateKindMismatch { required_pair, .. }
            | ReturnCoverageGapReason::MissingFxStartObservation { required_pair, .. } => {
                Some(PyCurrencyPair::from_inner(required_pair.clone()))
            }
            _ => None,
        }
    }

    #[getter]
    fn required_kind(&self) -> Option<PyFxRateKind> {
        match &self.inner {
            ReturnCoverageGapReason::MissingDirectFxCandidate { required_kind, .. }
            | ReturnCoverageGapReason::FxRateKindMismatch { required_kind, .. }
            | ReturnCoverageGapReason::MissingFxStartObservation { required_kind, .. } => {
                Some(PyFxRateKind::from_inner(*required_kind))
            }
            _ => None,
        }
    }

    #[getter]
    fn available_kinds(&self) -> Option<Vec<PyFxRateKind>> {
        match &self.inner {
            ReturnCoverageGapReason::FxRateKindMismatch {
                available_kinds, ..
            } => Some(
                available_kinds
                    .iter()
                    .map(|k| PyFxRateKind::from_inner(*k))
                    .collect(),
            ),
            _ => None,
        }
    }

    #[getter]
    fn requested_date(&self) -> Option<PyMarketDate> {
        match &self.inner {
            ReturnCoverageGapReason::MissingFxStartObservation { requested_date, .. } => {
                Some(PyMarketDate::from_inner(*requested_date))
            }
            _ => None,
        }
    }

    #[getter]
    fn boundary_evidence(&self) -> Option<PyFxBoundaryEvidence> {
        match &self.inner {
            ReturnCoverageGapReason::StaleFxStartObservation { evidence, .. }
            | ReturnCoverageGapReason::StaleFxEndObservation { evidence, .. } => {
                Some(PyFxBoundaryEvidence::from_inner(evidence.clone()))
            }
            _ => None,
        }
    }

    #[getter]
    fn maximum_staleness_calendar_days(&self) -> Option<u32> {
        match &self.inner {
            ReturnCoverageGapReason::StaleFxStartObservation {
                maximum_staleness_calendar_days,
                ..
            }
            | ReturnCoverageGapReason::StaleFxEndObservation {
                maximum_staleness_calendar_days,
                ..
            } => Some(*maximum_staleness_calendar_days),
            _ => None,
        }
    }

    fn __repr__(&self) -> String {
        format!("ReturnCoverageGapReason(kind='{}')", self.kind())
    }
}
