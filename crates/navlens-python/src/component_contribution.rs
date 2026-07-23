use crate::holding_position::PyHoldingPosition;
use crate::period_decimal_return::PyPeriodDecimalReturn;
use crate::portfolio_component_contribution::PyPortfolioComponentContribution;
use navlens_application::ComponentContribution;
use pyo3::prelude::*;

/// Python projection of a portfolio component mapped to its exact period return and calculated contribution.
#[pyclass(
    name = "ComponentContribution",
    frozen,
    module = "navlens._native",
    skip_from_py_object
)]
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PyComponentContribution {
    inner: ComponentContribution,
}

impl PyComponentContribution {
    pub(crate) fn from_inner(inner: ComponentContribution) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyComponentContribution {
    #[getter]
    fn holding(&self) -> PyHoldingPosition {
        PyHoldingPosition::from_inner(self.inner.holding().clone())
    }

    #[getter]
    fn period_return(&self) -> PyPeriodDecimalReturn {
        PyPeriodDecimalReturn::from_inner(*self.inner.period_return())
    }

    #[getter]
    fn contribution(&self) -> PyPortfolioComponentContribution {
        PyPortfolioComponentContribution::from_inner(*self.inner.contribution())
    }
}
