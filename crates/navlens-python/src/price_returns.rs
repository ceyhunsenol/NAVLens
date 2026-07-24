use crate::dated_decimal_return::PyDatedDecimalReturn;
use crate::error::validation_error;
use crate::period_decimal_return::PyPeriodDecimalReturn;
use crate::price_observation::PyPriceObservation;
use navlens_calendar::PriceSeries;
use navlens_core::FundId;
use pyo3::prelude::*;

fn build_price_series(
    fund_id: String,
    observations: Vec<PyPriceObservation>,
) -> PyResult<PriceSeries> {
    let fund_id = FundId::new(fund_id).map_err(validation_error)?;
    let observations = observations
        .into_iter()
        .map(PyPriceObservation::into_inner)
        .collect();
    PriceSeries::new(fund_id, observations).map_err(validation_error)
}

/// Converts a validated chronological unit-price series to decimal returns.
#[pyfunction]
pub(crate) fn calculate_price_returns(
    fund_id: String,
    observations: Vec<PyPriceObservation>,
) -> PyResult<Vec<PyDatedDecimalReturn>> {
    let series = build_price_series(fund_id, observations)?;
    series
        .decimal_returns()
        .map(|values| {
            values
                .into_iter()
                .map(PyDatedDecimalReturn::from_inner)
                .collect()
        })
        .map_err(validation_error)
}

/// Converts a validated chronological unit-price series to period decimal returns.
#[pyfunction]
pub(crate) fn calculate_price_period_returns(
    fund_id: String,
    observations: Vec<PyPriceObservation>,
) -> PyResult<Vec<PyPeriodDecimalReturn>> {
    let series = build_price_series(fund_id, observations)?;
    series
        .period_returns()
        .map(|values| {
            values
                .into_iter()
                .map(PyPeriodDecimalReturn::from_inner)
                .collect()
        })
        .map_err(validation_error)
}
