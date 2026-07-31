use crate::error::validation_error;
use navlens_core::FxRateKind;
use pyo3::prelude::*;

/// Python projection of an FX rate economic kind.
#[pyclass(
    name = "FxRateKind",
    frozen,
    module = "navlens._native",
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub(crate) struct PyFxRateKind {
    inner: FxRateKind,
}

impl PyFxRateKind {
    pub(crate) const fn from_inner(inner: FxRateKind) -> Self {
        Self { inner }
    }

    pub(crate) const fn into_inner(self) -> FxRateKind {
        self.inner
    }
}

pub(crate) fn parse_fx_rate_kind(value: &str) -> Result<FxRateKind, String> {
    match value.to_ascii_lowercase().as_str() {
        "non_cash_buying" => Ok(FxRateKind::NonCashBuying),
        "non_cash_selling" => Ok(FxRateKind::NonCashSelling),
        "cash_buying" => Ok(FxRateKind::CashBuying),
        "cash_selling" => Ok(FxRateKind::CashSelling),
        _ => Err(format!(
            "unknown FX rate kind '{value}'; expected one of: non_cash_buying, non_cash_selling, cash_buying, cash_selling"
        )),
    }
}

pub(crate) fn fx_rate_kind_name(kind: FxRateKind) -> &'static str {
    match kind {
        FxRateKind::NonCashBuying => "non_cash_buying",
        FxRateKind::NonCashSelling => "non_cash_selling",
        FxRateKind::CashBuying => "cash_buying",
        FxRateKind::CashSelling => "cash_selling",
    }
}

#[allow(clippy::trivially_copy_pass_by_ref)]
#[pymethods]
impl PyFxRateKind {
    #[new]
    fn new(value: &str) -> PyResult<Self> {
        parse_fx_rate_kind(value)
            .map(Self::from_inner)
            .map_err(validation_error)
    }

    #[getter]
    fn name(&self) -> &'static str {
        fx_rate_kind_name(self.inner)
    }

    fn __repr__(&self) -> String {
        format!("FxRateKind('{}')", fx_rate_kind_name(self.inner))
    }

    fn __str__(&self) -> &'static str {
        fx_rate_kind_name(self.inner)
    }
}
