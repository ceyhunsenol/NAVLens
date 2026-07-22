use super::calculation::{WEIGHT_TOLERANCE, calculate_weighted_return};
use crate::{CoreError, DecimalReturn, ExpenseRate, PortfolioComponent};

/// Input to the transparent weighted-return baseline estimator.
#[derive(Clone, Debug, PartialEq)]
pub struct PortfolioEstimate<'a> {
    pub components: &'a [PortfolioComponent],
    pub daily_expense_rate: ExpenseRate,
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
        if self.components.is_empty() {
            return Err(CoreError::EmptyPortfolio);
        }

        let result = calculate_weighted_return(self.components);

        if (result.weight_sum - 1.0).abs() > WEIGHT_TOLERANCE {
            return Err(CoreError::WeightsDoNotSumToOne(result.weight_sum));
        }

        DecimalReturn::new(result.gross_return - self.daily_expense_rate.value())
    }
}
