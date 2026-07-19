use crate::error::validation_error;
use crate::portfolio_return_estimate::PortfolioReturnEstimate;
use navlens_application::{
    EstimatePortfolioReturnCommand, WeightedMarketReturnInput,
    estimate_portfolio_return as execute_estimate,
};
use pyo3::prelude::*;

#[pyfunction]
#[pyo3(signature = (components, daily_expense_rate=0.0))]
pub(crate) fn estimate_portfolio_return(
    components: Vec<(f64, f64)>,
    daily_expense_rate: f64,
) -> PyResult<PortfolioReturnEstimate> {
    execute(components, daily_expense_rate).map_err(validation_error)
}

fn execute(
    components: Vec<(f64, f64)>,
    daily_expense_rate: f64,
) -> Result<PortfolioReturnEstimate, navlens_application::ApplicationError> {
    let components = components
        .into_iter()
        .map(|(weight, market_return)| WeightedMarketReturnInput::new(weight, market_return))
        .collect();
    let command = EstimatePortfolioReturnCommand::new(components, daily_expense_rate);
    let result = execute_estimate(&command)?;

    Ok(PortfolioReturnEstimate::new(
        result.estimated_return().value(),
    ))
}

#[cfg(test)]
mod tests {
    use super::execute;

    #[test]
    fn delegates_estimation_to_application_layer() {
        let result = execute(vec![(0.7, 0.02), (0.3, -0.01)], 0.0001)
            .expect("valid inputs must produce an estimate");

        assert_eq!(result, super::PortfolioReturnEstimate::new(0.0109));
    }

    #[test]
    fn preserves_domain_validation() {
        let result = execute(vec![(0.8, 0.02), (0.3, -0.01)], 0.0001);

        assert!(result.is_err());
    }
}
