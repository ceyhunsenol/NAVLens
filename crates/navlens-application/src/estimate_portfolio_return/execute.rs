use super::{
    EstimatePortfolioReturnCommand, EstimatePortfolioReturnResult, WeightedMarketReturnInput,
};
use crate::ApplicationError;
use navlens_core::{
    DecimalReturn, ExpenseRate, PortfolioComponent, PortfolioEstimate, PortfolioWeight,
};

/// Estimates a net portfolio return from transport-independent application input.
///
/// # Errors
/// Returns [`ApplicationError::InvalidEstimateInput`] when a component, expense
/// rate, or the resulting portfolio violates a domain invariant.
pub fn estimate_portfolio_return(
    command: &EstimatePortfolioReturnCommand,
) -> Result<EstimatePortfolioReturnResult, ApplicationError> {
    let components = command
        .components()
        .iter()
        .map(to_domain_component)
        .collect::<Result<Vec<_>, _>>()?;
    let daily_expense_rate = ExpenseRate::new(command.daily_expense_rate())?;
    let estimate = PortfolioEstimate {
        components: &components,
        daily_expense_rate,
    };

    Ok(EstimatePortfolioReturnResult::new(estimate.calculate()?))
}

fn to_domain_component(
    input: &WeightedMarketReturnInput,
) -> Result<PortfolioComponent, ApplicationError> {
    Ok(PortfolioComponent {
        weight: PortfolioWeight::new(input.weight())?,
        market_return: DecimalReturn::new(input.market_return())?,
    })
}
