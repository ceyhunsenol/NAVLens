use crate::error::validation_error;
use navlens_calendar::PriceAdjustment;
use pyo3::prelude::*;

/// Python projection of a corporate-action price adjustment policy.
#[pyclass(
    name = "PriceAdjustment",
    frozen,
    module = "navlens._native",
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub(crate) struct PyPriceAdjustment {
    inner: PriceAdjustment,
}

impl PyPriceAdjustment {
    pub(crate) const fn from_inner(inner: PriceAdjustment) -> Self {
        Self { inner }
    }

    pub(crate) const fn into_inner(self) -> PriceAdjustment {
        self.inner
    }
}

pub(crate) fn parse_price_adjustment(value: &str) -> Result<PriceAdjustment, String> {
    match value.to_ascii_lowercase().as_str() {
        "unadjusted" => Ok(PriceAdjustment::Unadjusted),
        "split_adjusted" => Ok(PriceAdjustment::SplitAdjusted),
        "total_return_adjusted" => Ok(PriceAdjustment::TotalReturnAdjusted),
        _ => Err(format!(
            "unknown price adjustment '{value}'; expected one of: unadjusted, split_adjusted, total_return_adjusted"
        )),
    }
}

pub(crate) fn price_adjustment_name(adjustment: PriceAdjustment) -> &'static str {
    match adjustment {
        PriceAdjustment::Unadjusted => "unadjusted",
        PriceAdjustment::SplitAdjusted => "split_adjusted",
        PriceAdjustment::TotalReturnAdjusted => "total_return_adjusted",
    }
}

#[allow(clippy::trivially_copy_pass_by_ref)]
#[pymethods]
impl PyPriceAdjustment {
    #[new]
    fn new(value: &str) -> PyResult<Self> {
        parse_price_adjustment(value)
            .map(Self::from_inner)
            .map_err(validation_error)
    }

    #[getter]
    fn name(&self) -> &'static str {
        price_adjustment_name(self.inner)
    }

    fn __repr__(&self) -> String {
        format!("PriceAdjustment('{}')", price_adjustment_name(self.inner))
    }

    fn __str__(&self) -> &'static str {
        price_adjustment_name(self.inner)
    }
}
