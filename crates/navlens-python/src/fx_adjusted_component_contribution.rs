use crate::currency_return_adjustment::PyCurrencyReturnAdjustment;
use crate::holding_position::PyHoldingPosition;
use crate::period_decimal_return::PyPeriodDecimalReturn;
use crate::portfolio_component_contribution::PyPortfolioComponentContribution;
use navlens_application::FxAdjustedComponentContribution;
use pyo3::prelude::*;

#[pyclass(
    name = "FxAdjustedComponentContribution",
    frozen,
    module = "navlens._native",
    eq,
    from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyFxAdjustedComponentContribution {
    inner: FxAdjustedComponentContribution,
}

impl PyFxAdjustedComponentContribution {
    pub(crate) const fn from_inner(inner: FxAdjustedComponentContribution) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyFxAdjustedComponentContribution {
    #[getter]
    fn holding(&self) -> PyHoldingPosition {
        PyHoldingPosition::from_inner(self.inner.holding().clone())
    }

    #[getter]
    fn security_period_return(&self) -> PyPeriodDecimalReturn {
        PyPeriodDecimalReturn::from_inner(*self.inner.security_period_return())
    }

    #[getter]
    fn currency_adjustment(&self) -> PyCurrencyReturnAdjustment {
        PyCurrencyReturnAdjustment::from_inner(self.inner.currency_adjustment().clone())
    }

    #[getter]
    fn effective_base_currency_return(&self) -> f64 {
        self.inner.effective_base_currency_return().value()
    }

    #[getter]
    fn contribution(&self) -> PyPortfolioComponentContribution {
        PyPortfolioComponentContribution::from_inner(*self.inner.contribution())
    }
}
