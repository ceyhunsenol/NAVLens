use crate::dated_decimal_return::PyDatedDecimalReturn;
use crate::error::validation_error;
use crate::price_observation::PyPriceObservation;
use navlens_calendar::PriceSeries;
use navlens_core::FundId;
use pyo3::prelude::*;

/// Converts a validated chronological unit-price series to decimal returns.
#[pyfunction]
pub(crate) fn calculate_price_returns(
    fund_id: String,
    observations: Vec<PyPriceObservation>,
) -> PyResult<Vec<PyDatedDecimalReturn>> {
    let fund_id = FundId::new(fund_id).map_err(validation_error)?;
    let observations = observations
        .into_iter()
        .map(PyPriceObservation::into_inner)
        .collect();
    let series = PriceSeries::new(fund_id, observations).map_err(validation_error)?;
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
