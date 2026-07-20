//! Thin `PyO3` mappings for the public `NAVLens` Python package.

mod backtest_metrics;
mod backtest_observation;
mod dated_decimal_return;
mod error;
mod estimate_portfolio;
mod evaluate_backtest;
mod market_date;
mod model_descriptor;
mod portfolio_return_estimate;
mod prediction_request;
mod price_observation;
mod price_returns;
mod return_prediction;
mod unit_price;
mod utc_timestamp;

use backtest_metrics::{PyBacktestMetrics, PyIntervalMetrics};
use backtest_observation::PyBacktestObservation;
use dated_decimal_return::PyDatedDecimalReturn;
use error::NavlensValidationError;
use estimate_portfolio::estimate_portfolio_return;
use evaluate_backtest::evaluate_backtest as evaluate_backtest_fn;
use market_date::PyMarketDate;
use model_descriptor::PyModelDescriptor;
use portfolio_return_estimate::PortfolioReturnEstimate;
use prediction_request::PyPredictionRequest;
use price_observation::PyPriceObservation;
use price_returns::calculate_price_returns;
use pyo3::prelude::*;
use return_prediction::{PyReturnPrediction, create_return_prediction};
use unit_price::PyUnitPrice;
use utc_timestamp::PyUtcTimestamp;

#[pymodule(gil_used = false)]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add(
        "NavlensValidationError",
        module.py().get_type::<NavlensValidationError>(),
    )?;
    module.add_class::<PyMarketDate>()?;
    module.add_class::<PyUnitPrice>()?;
    module.add_class::<PyPriceObservation>()?;
    module.add_class::<PyDatedDecimalReturn>()?;
    module.add_class::<PyUtcTimestamp>()?;
    module.add_class::<PyModelDescriptor>()?;
    module.add_class::<PyPredictionRequest>()?;
    module.add_class::<PyReturnPrediction>()?;
    module.add_class::<PyBacktestObservation>()?;
    module.add_class::<PyIntervalMetrics>()?;
    module.add_class::<PyBacktestMetrics>()?;
    module.add_class::<PortfolioReturnEstimate>()?;
    module.add_function(wrap_pyfunction!(estimate_portfolio_return, module)?)?;
    module.add_function(wrap_pyfunction!(create_return_prediction, module)?)?;
    module.add_function(wrap_pyfunction!(calculate_price_returns, module)?)?;
    module.add_function(wrap_pyfunction!(evaluate_backtest_fn, module)?)?;
    Ok(())
}
