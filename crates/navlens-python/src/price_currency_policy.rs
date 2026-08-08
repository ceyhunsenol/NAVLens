use crate::error::validation_error;
use navlens_application::PriceCurrencyPolicy;
use pyo3::prelude::*;

#[pyclass(
    name = "PriceCurrencyPolicy",
    frozen,
    module = "navlens._native",
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub(crate) struct PyPriceCurrencyPolicy {
    inner: PriceCurrencyPolicy,
}

impl PyPriceCurrencyPolicy {
    pub(crate) const fn from_inner(inner: PriceCurrencyPolicy) -> Self {
        Self { inner }
    }

    pub(crate) const fn into_inner(self) -> PriceCurrencyPolicy {
        self.inner
    }
}

pub(crate) fn parse_price_currency_policy(value: &str) -> Result<PriceCurrencyPolicy, String> {
    match value.to_ascii_lowercase().as_str() {
        "fund_base_only" => Ok(PriceCurrencyPolicy::FundBaseOnly),
        "permit_foreign" => Ok(PriceCurrencyPolicy::PermitForeign),
        _ => Err(format!(
            "unknown price currency policy '{value}'; expected one of: fund_base_only, permit_foreign"
        )),
    }
}

pub(crate) fn price_currency_policy_name(policy: PriceCurrencyPolicy) -> &'static str {
    match policy {
        PriceCurrencyPolicy::FundBaseOnly => "fund_base_only",
        PriceCurrencyPolicy::PermitForeign => "permit_foreign",
    }
}

#[allow(clippy::trivially_copy_pass_by_ref)]
#[pymethods]
impl PyPriceCurrencyPolicy {
    #[new]
    fn new(value: &str) -> PyResult<Self> {
        parse_price_currency_policy(value)
            .map(Self::from_inner)
            .map_err(validation_error)
    }

    #[getter]
    fn name(&self) -> &'static str {
        price_currency_policy_name(self.inner)
    }

    fn __repr__(&self) -> String {
        format!(
            "PriceCurrencyPolicy('{}')",
            price_currency_policy_name(self.inner)
        )
    }

    fn __str__(&self) -> &'static str {
        price_currency_policy_name(self.inner)
    }
}
