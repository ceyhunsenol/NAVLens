use crate::fx_adjustment_evidence::PyFxAdjustmentEvidence;
use navlens_application::CurrencyReturnAdjustment;
use pyo3::prelude::*;

#[pyclass(
    name = "CurrencyReturnAdjustment",
    frozen,
    module = "navlens._native",
    eq,
    from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyCurrencyReturnAdjustment {
    inner: CurrencyReturnAdjustment,
}

impl PyCurrencyReturnAdjustment {
    pub(crate) const fn from_inner(inner: CurrencyReturnAdjustment) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyCurrencyReturnAdjustment {
    #[getter]
    fn is_applied(&self) -> bool {
        matches!(self.inner, CurrencyReturnAdjustment::Applied(_))
    }

    #[getter]
    fn is_not_required(&self) -> bool {
        matches!(self.inner, CurrencyReturnAdjustment::NotRequired)
    }

    #[getter]
    fn applied_evidence(&self) -> Option<PyFxAdjustmentEvidence> {
        match &self.inner {
            CurrencyReturnAdjustment::Applied(evidence) => {
                Some(PyFxAdjustmentEvidence::from_inner(evidence.clone()))
            }
            CurrencyReturnAdjustment::NotRequired => None,
        }
    }
}
