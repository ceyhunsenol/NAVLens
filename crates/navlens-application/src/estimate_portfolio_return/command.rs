#[derive(Clone, Debug, PartialEq)]
pub struct WeightedMarketReturnInput {
    weight: f64,
    market_return: f64,
}

impl WeightedMarketReturnInput {
    #[must_use]
    pub const fn new(weight: f64, market_return: f64) -> Self {
        Self {
            weight,
            market_return,
        }
    }

    #[must_use]
    pub const fn weight(&self) -> f64 {
        self.weight
    }

    #[must_use]
    pub const fn market_return(&self) -> f64 {
        self.market_return
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct EstimatePortfolioReturnCommand {
    components: Vec<WeightedMarketReturnInput>,
    daily_expense_rate: f64,
}

impl EstimatePortfolioReturnCommand {
    #[must_use]
    pub const fn new(components: Vec<WeightedMarketReturnInput>, daily_expense_rate: f64) -> Self {
        Self {
            components,
            daily_expense_rate,
        }
    }

    #[must_use]
    pub fn components(&self) -> &[WeightedMarketReturnInput] {
        &self.components
    }

    #[must_use]
    pub const fn daily_expense_rate(&self) -> f64 {
        self.daily_expense_rate
    }
}
