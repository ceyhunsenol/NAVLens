//! Canonical financial types and deterministic calculations for `NAVLens`.

use std::error::Error;
use std::fmt::{Display, Formatter};

/// A decimal return where `0.01` represents one percent.
#[derive(Clone, Copy, Debug, Default, PartialEq, PartialOrd)]
pub struct DecimalReturn(f64);

impl DecimalReturn {
    /// Creates a finite decimal return.
    ///
    /// # Errors
    /// Returns [`CoreError::NonFiniteNumber`] for NaN or infinity.
    pub fn new(value: f64) -> Result<Self, CoreError> {
        if value.is_finite() {
            Ok(Self(value))
        } else {
            Err(CoreError::NonFiniteNumber)
        }
    }

    #[must_use]
    pub const fn value(self) -> f64 {
        self.0
    }
}

/// One component of a fund portfolio and its observed market return.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PortfolioComponent {
    pub weight: f64,
    pub market_return: DecimalReturn,
}

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

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum CoreError {
    EmptyPortfolio,
    NegativeWeight(f64),
    NonFiniteNumber,
    WeightsDoNotSumToOne(f64),
}

impl Display for CoreError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::EmptyPortfolio => formatter.write_str("portfolio cannot be empty"),
            Self::NegativeWeight(weight) => {
                write!(formatter, "weight cannot be negative: {weight}")
            }
            Self::NonFiniteNumber => formatter.write_str("number must be finite"),
            Self::WeightsDoNotSumToOne(sum) => {
                write!(formatter, "portfolio weights must sum to one; got {sum}")
            }
        }
    }
}

impl Error for CoreError {}

#[cfg(test)]
mod tests {
    use super::*;

    fn decimal_return(value: f64) -> DecimalReturn {
        DecimalReturn::new(value).expect("test return should be finite")
    }

    #[test]
    fn calculates_weighted_return_after_expenses() {
        let components = [
            PortfolioComponent {
                weight: 0.7,
                market_return: decimal_return(0.02),
            },
            PortfolioComponent {
                weight: 0.2,
                market_return: decimal_return(-0.01),
            },
            PortfolioComponent {
                weight: 0.1,
                market_return: decimal_return(0.001),
            },
        ];
        let estimate = PortfolioEstimate {
            components: &components,
            daily_expense_rate: decimal_return(0.0001),
        };

        let result = estimate.calculate().expect("valid portfolio");
        assert!((result.value() - 0.012).abs() < 1e-12);
    }

    #[test]
    fn rejects_invalid_weight_sum() {
        let components = [PortfolioComponent {
            weight: 0.8,
            market_return: decimal_return(0.01),
        }];
        let estimate = PortfolioEstimate {
            components: &components,
            daily_expense_rate: decimal_return(0.0),
        };

        assert_eq!(
            estimate.calculate(),
            Err(CoreError::WeightsDoNotSumToOne(0.8))
        );
    }

    #[test]
    fn rejects_non_finite_returns() {
        assert_eq!(
            DecimalReturn::new(f64::NAN),
            Err(CoreError::NonFiniteNumber)
        );
    }
}
