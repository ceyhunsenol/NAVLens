use navlens_core::{
    CoreError, DecimalReturn, PortfolioComponent, PortfolioComponentContribution, PortfolioWeight,
};

/// Calculates the component and its contribution based on its weight and effective decimal return.
pub(crate) fn calculate_canonical_contribution(
    weight: PortfolioWeight,
    effective_return: DecimalReturn,
) -> Result<(PortfolioComponent, PortfolioComponentContribution), CoreError> {
    let component = PortfolioComponent {
        weight,
        market_return: effective_return,
    };
    let contribution = PortfolioComponentContribution::calculate(&component)?;
    Ok((component, contribution))
}
