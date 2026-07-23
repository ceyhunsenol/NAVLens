use super::component::PortfolioComponent;
use super::component_contribution::PortfolioComponentContribution;
use crate::CoreError;

pub(super) const WEIGHT_TOLERANCE: f64 = 1e-9;

pub(super) struct WeightedReturnSum {
    pub weight_sum: f64,
    pub gross_return: f64,
}

pub(super) fn calculate_weighted_return(
    components: &[PortfolioComponent],
) -> Result<WeightedReturnSum, CoreError> {
    let mut weight_sum = 0.0;
    let mut gross_return = 0.0;

    for component in components {
        weight_sum += component.weight.value();
        let contribution = PortfolioComponentContribution::calculate(component)?;
        gross_return += contribution.weighted_contribution().value();
    }

    Ok(WeightedReturnSum {
        weight_sum,
        gross_return,
    })
}
