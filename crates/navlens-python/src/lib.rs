//! Thin `PyO3` mappings for the public `NAVLens` Python package.

mod error;
mod estimate_portfolio;
mod portfolio_return_estimate;

use error::NavlensValidationError;
use estimate_portfolio::estimate_portfolio_return;
use portfolio_return_estimate::PortfolioReturnEstimate;
use pyo3::prelude::*;

#[pymodule(gil_used = false)]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add(
        "NavlensValidationError",
        module.py().get_type::<NavlensValidationError>(),
    )?;
    module.add_class::<PortfolioReturnEstimate>()?;
    module.add_function(wrap_pyfunction!(estimate_portfolio_return, module)?)?;
    Ok(())
}
