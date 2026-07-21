use crate::error::validation_error;
use navlens_core::AssetClass;
use pyo3::prelude::*;

/// Python projection of a provider-neutral asset classification.
#[pyclass(
    name = "AssetClass",
    frozen,
    module = "navlens._native",
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub(crate) struct PyAssetClass {
    inner: AssetClass,
}

impl PyAssetClass {
    pub(crate) const fn from_inner(inner: AssetClass) -> Self {
        Self { inner }
    }

    pub(crate) const fn into_inner(self) -> AssetClass {
        self.inner
    }
}

pub(crate) fn parse_asset_class(value: &str) -> Result<AssetClass, String> {
    match value.to_ascii_lowercase().as_str() {
        "equity" => Ok(AssetClass::Equity),
        "debt_security" => Ok(AssetClass::DebtSecurity),
        "repo" => Ok(AssetClass::Repo),
        "deposit" => Ok(AssetClass::Deposit),
        "investment_fund" => Ok(AssetClass::InvestmentFund),
        "exchange_traded_fund" => Ok(AssetClass::ExchangeTradedFund),
        "precious_metal" => Ok(AssetClass::PreciousMetal),
        "derivative" => Ok(AssetClass::Derivative),
        "cash" => Ok(AssetClass::Cash),
        "other" => Ok(AssetClass::Other),
        _ => Err(format!(
            "unknown asset class '{value}'; expected one of: equity, debt_security, \
             repo, deposit, investment_fund, exchange_traded_fund, precious_metal, \
             derivative, cash, other"
        )),
    }
}

pub(crate) fn asset_class_name(asset_class: AssetClass) -> &'static str {
    match asset_class {
        AssetClass::Equity => "equity",
        AssetClass::DebtSecurity => "debt_security",
        AssetClass::Repo => "repo",
        AssetClass::Deposit => "deposit",
        AssetClass::InvestmentFund => "investment_fund",
        AssetClass::ExchangeTradedFund => "exchange_traded_fund",
        AssetClass::PreciousMetal => "precious_metal",
        AssetClass::Derivative => "derivative",
        AssetClass::Cash => "cash",
        AssetClass::Other | _ => "other",
    }
}

#[allow(clippy::trivially_copy_pass_by_ref)]
#[pymethods]
impl PyAssetClass {
    #[new]
    fn new(value: &str) -> PyResult<Self> {
        parse_asset_class(value)
            .map(Self::from_inner)
            .map_err(validation_error)
    }

    #[getter]
    fn name(&self) -> &'static str {
        asset_class_name(self.inner)
    }

    fn __repr__(&self) -> String {
        format!("AssetClass('{}')", asset_class_name(self.inner))
    }

    fn __str__(&self) -> &'static str {
        asset_class_name(self.inner)
    }
}
