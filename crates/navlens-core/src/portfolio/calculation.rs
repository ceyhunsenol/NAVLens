use super::component::PortfolioComponent;

pub(super) const WEIGHT_TOLERANCE: f64 = 1e-9;

pub(super) struct WeightedReturnSum {
    pub weight_sum: f64,
    pub gross_return: f64,
}

pub(super) fn calculate_weighted_return(components: &[PortfolioComponent]) -> WeightedReturnSum {
    let mut weight_sum = 0.0;
    let mut gross_return = 0.0;

    for component in components {
        weight_sum += component.weight.value();
        gross_return += component.weight.value() * component.market_return.value();
    }

    WeightedReturnSum {
        weight_sum,
        gross_return,
    }
}
