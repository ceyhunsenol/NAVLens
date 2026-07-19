use crate::{CoreError, DecimalReturn, PortfolioComponent};

/// Input to the transparent weighted-return baseline estimator.
#[derive(Clone, Debug, PartialEq)]
pub struct PortfolioEstimate<'a> {
    pub components: &'a [PortfolioComponent],
    pub daily_expense_rate: DecimalReturn,
}

impl PortfolioEstimate<'_> {
    /// Estimates the fund return using disclosed portfolio weights.
    ///
    /// Weights must be finite, non-negative, and sum to one within a small
    /// tolerance. Expenses are subtracted after the weighted market return.
    ///
    /// # Errors
    /// Returns an error when the portfolio is empty or its weights are invalid.
    pub fn calculate(&self) -> Result<DecimalReturn, CoreError> {
        const WEIGHT_TOLERANCE: f64 = 1e-9;

        if self.components.is_empty() {
            return Err(CoreError::EmptyPortfolio);
        }

        let mut weight_sum = 0.0;
        let mut gross_return = 0.0;

        for component in self.components {
            if !component.weight.is_finite() {
                return Err(CoreError::NonFiniteNumber);
            }
            if component.weight < 0.0 {
                return Err(CoreError::NegativeWeight(component.weight));
            }
            weight_sum += component.weight;
            gross_return += component.weight * component.market_return.value();
        }

        if (weight_sum - 1.0).abs() > WEIGHT_TOLERANCE {
            return Err(CoreError::WeightsDoNotSumToOne(weight_sum));
        }

        DecimalReturn::new(gross_return - self.daily_expense_rate.value())
    }
}
