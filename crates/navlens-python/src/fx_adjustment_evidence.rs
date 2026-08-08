use crate::currency_pair::PyCurrencyPair;
use crate::fx_boundary_evidence::PyFxBoundaryEvidence;
use crate::fx_rate_kind::PyFxRateKind;
use navlens_application::FxAdjustmentEvidence;
use pyo3::prelude::*;

#[pyclass(
    name = "FxAdjustmentEvidence",
    frozen,
    module = "navlens._native",
    eq,
    from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyFxAdjustmentEvidence {
    inner: FxAdjustmentEvidence,
}

impl PyFxAdjustmentEvidence {
    pub(crate) const fn from_inner(inner: FxAdjustmentEvidence) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyFxAdjustmentEvidence {
    #[getter]
    fn required_pair(&self) -> PyCurrencyPair {
        PyCurrencyPair::from_inner(self.inner.pair().clone())
    }

    #[getter]
    fn required_kind(&self) -> PyFxRateKind {
        PyFxRateKind::from_inner(self.inner.kind())
    }

    #[getter]
    fn start(&self) -> PyFxBoundaryEvidence {
        PyFxBoundaryEvidence::from_inner(self.inner.start().clone())
    }

    #[getter]
    fn end(&self) -> PyFxBoundaryEvidence {
        PyFxBoundaryEvidence::from_inner(self.inner.end().clone())
    }

    #[getter]
    fn fx_return(&self) -> f64 {
        self.inner.fx_return().value()
    }
}
