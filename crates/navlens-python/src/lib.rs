//! Thin `PyO3` mappings for the public `NAVLens` Python package.

mod align_holdings_prices;
mod alignment_policy;
mod asset_class;
mod backtest_metrics;
mod backtest_observation;
mod calculate_return_contribution;
mod component_contribution;
mod coverage_gap_reason;
mod covered_holding_price;
mod currency_code;
mod dated_decimal_return;
mod error;
mod estimate_portfolio;
mod evaluate_backtest;
mod fund_return_reconciliation;
mod fund_return_reconciliation_result;
mod holding_position;
mod market_date;
mod model_descriptor;
mod period_decimal_return;
mod portfolio_component_contribution;
mod portfolio_coverage_report;
mod portfolio_return_contribution;
mod portfolio_return_estimate;
mod prediction_request;
mod price_adjustment;
mod price_observation;
mod price_returns;
mod reconcile_fund_return;
mod return_contribution_result;
mod return_coverage_gap;
mod return_coverage_gap_reason;
mod return_period;
mod return_prediction;
mod security_price_history_candidate;
mod security_price_observation;
mod security_price_series;
mod uncovered_holding;
mod unit_price;
mod utc_timestamp;

use align_holdings_prices::align_holdings_prices as align_holdings_prices_fn;
use alignment_policy::PyAlignmentPolicy;
use asset_class::PyAssetClass;
use backtest_metrics::{PyBacktestMetrics, PyIntervalMetrics};
use backtest_observation::PyBacktestObservation;
use coverage_gap_reason::PyCoverageGapReason;
use covered_holding_price::PyCoveredHoldingPrice;
use currency_code::PyCurrencyCode;
use dated_decimal_return::PyDatedDecimalReturn;
use error::NavlensValidationError;
use estimate_portfolio::estimate_portfolio_return;
use evaluate_backtest::evaluate_backtest as evaluate_backtest_fn;
use holding_position::PyHoldingPosition;
use market_date::PyMarketDate;
use model_descriptor::PyModelDescriptor;
use period_decimal_return::PyPeriodDecimalReturn;
use portfolio_coverage_report::PyPortfolioCoverageReport;
use portfolio_return_estimate::PortfolioReturnEstimate;
use prediction_request::PyPredictionRequest;
use price_adjustment::PyPriceAdjustment;
use price_observation::PyPriceObservation;
use price_returns::{calculate_price_period_returns, calculate_price_returns};
use pyo3::prelude::*;
use return_contribution_result::PyReturnContributionResult;
use return_coverage_gap::PyReturnCoverageGap;
use return_coverage_gap_reason::PyReturnCoverageGapReason;
use return_period::PyReturnPeriod;
use return_prediction::{PyReturnPrediction, create_return_prediction};
use security_price_history_candidate::PySecurityPriceHistoryCandidate;
use security_price_observation::PySecurityPriceObservation;
use security_price_series::PySecurityPriceSeries;
use uncovered_holding::PyUncoveredHolding;
use unit_price::PyUnitPrice;
use utc_timestamp::PyUtcTimestamp;

#[pymodule(gil_used = false)]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add(
        "NavlensValidationError",
        module.py().get_type::<NavlensValidationError>(),
    )?;
    module.add_class::<PyAssetClass>()?;
    module.add_class::<PyCurrencyCode>()?;
    module.add_class::<PyPriceAdjustment>()?;
    module.add_class::<PyMarketDate>()?;
    module.add_class::<PyUnitPrice>()?;
    module.add_class::<PyHoldingPosition>()?;
    module.add_class::<PyPriceObservation>()?;
    module.add_class::<PySecurityPriceObservation>()?;
    module.add_class::<PySecurityPriceSeries>()?;
    module.add_class::<PySecurityPriceHistoryCandidate>()?;
    module.add_class::<PyAlignmentPolicy>()?;
    module.add_class::<PyCoverageGapReason>()?;
    module.add_class::<PyCoveredHoldingPrice>()?;
    module.add_class::<PyUncoveredHolding>()?;
    module.add_class::<PyDatedDecimalReturn>()?;
    module.add_class::<PyReturnPeriod>()?;
    module.add_class::<PyPeriodDecimalReturn>()?;
    module.add_class::<PyUtcTimestamp>()?;
    module.add_class::<PyModelDescriptor>()?;
    module.add_class::<PyPredictionRequest>()?;
    module.add_class::<PyReturnPrediction>()?;
    module.add_class::<PyBacktestObservation>()?;
    module.add_class::<PyIntervalMetrics>()?;
    module.add_class::<PyBacktestMetrics>()?;
    module.add_class::<PortfolioReturnEstimate>()?;
    module.add_class::<PyPortfolioCoverageReport>()?;
    module.add_class::<PyReturnCoverageGapReason>()?;
    module.add_class::<PyReturnCoverageGap>()?;
    module.add_class::<portfolio_return_contribution::PyPortfolioReturnContribution>()?;
    module.add_class::<portfolio_component_contribution::PyPortfolioComponentContribution>()?;
    module.add_class::<component_contribution::PyComponentContribution>()?;
    module.add_class::<PyReturnContributionResult>()?;
    module.add_class::<fund_return_reconciliation::PyFundReturnReconciliation>()?;
    module.add_class::<fund_return_reconciliation_result::PyFundReturnReconciliationResult>()?;
    module.add_function(wrap_pyfunction!(estimate_portfolio_return, module)?)?;
    module.add_function(wrap_pyfunction!(create_return_prediction, module)?)?;
    module.add_function(wrap_pyfunction!(calculate_price_returns, module)?)?;
    module.add_function(wrap_pyfunction!(calculate_price_period_returns, module)?)?;
    module.add_function(wrap_pyfunction!(evaluate_backtest_fn, module)?)?;
    module.add_function(wrap_pyfunction!(align_holdings_prices_fn, module)?)?;
    module.add_function(wrap_pyfunction!(
        calculate_return_contribution::calculate_return_contribution,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(
        reconcile_fund_return::reconcile_fund_return,
        module
    )?)?;
    Ok(())
}
