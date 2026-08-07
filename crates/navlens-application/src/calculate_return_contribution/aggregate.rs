use navlens_core::{CoreError, PortfolioComponent, PortfolioReturnContribution};

/// Calculates the aggregate portfolio return contribution.
pub(crate) fn calculate_aggregate_contribution(
    components: &[PortfolioComponent],
) -> Result<PortfolioReturnContribution, CoreError> {
    PortfolioReturnContribution::calculate(components)
}
