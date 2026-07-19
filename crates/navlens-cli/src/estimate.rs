use crate::command::EstimateArgs;
use navlens_application::{
    ApplicationError, EstimatePortfolioReturnCommand, WeightedMarketReturnInput,
    estimate_portfolio_return,
};

pub fn execute(arguments: EstimateArgs) -> Result<String, ApplicationError> {
    let components = arguments
        .components
        .into_iter()
        .map(|component| WeightedMarketReturnInput::new(component.weight, component.market_return))
        .collect();
    let command = EstimatePortfolioReturnCommand::new(components, arguments.daily_expense_rate);
    let result = estimate_portfolio_return(&command)?
        .estimated_return()
        .value();

    Ok(format!(
        "estimated_return_decimal={result:.10}\nestimated_return_percent={:.6}%",
        result * 100.0
    ))
}
