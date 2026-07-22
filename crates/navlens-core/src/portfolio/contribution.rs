use super::calculation::{WEIGHT_TOLERANCE, calculate_weighted_return};
use super::component::PortfolioComponent;
use super::weight::PortfolioWeight;
use crate::{CoreError, DecimalReturn};

/// The observed return contribution of a portfolio's covered holdings.
///
/// Combines the weighted gross return of available portfolio components with the total
/// return coverage weight.
///
/// An empty component list yields an `observed_contribution` of zero and a `return_coverage` of zero.
/// This represents the additive identity of observed contributions and does not imply that an
/// unobserved or missing portfolio has a 0% return.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PortfolioReturnContribution {
    observed_contribution: DecimalReturn,
    return_coverage: PortfolioWeight,
}

impl PortfolioReturnContribution {
    /// Calculates the observed return contribution from a sequence of portfolio components.
    ///
    /// The total weight of the components must not exceed `1.0` (plus floating-point tolerance).
    /// Weights are not renormalized and expense rates are not applied.
    ///
    /// # Errors
    /// Returns [`CoreError::ReturnCoverageExceedsFundTotal`] if the sum of component weights exceeds
    /// `1.0` plus tolerance, or [`CoreError::NonFiniteNumber`] / [`CoreError::PortfolioWeightOutOfRange`] if
    /// component calculations yield invalid values.
    pub fn calculate(components: &[PortfolioComponent]) -> Result<Self, CoreError> {
        if components.is_empty() {
            return Ok(Self {
                observed_contribution: DecimalReturn::new(0.0)?,
                return_coverage: PortfolioWeight::new(0.0)?,
            });
        }

        let result = calculate_weighted_return(components);

        if !result.weight_sum.is_finite() || !result.gross_return.is_finite() {
            return Err(CoreError::NonFiniteNumber);
        }

        if result.weight_sum > 1.0 + WEIGHT_TOLERANCE {
            return Err(CoreError::ReturnCoverageExceedsFundTotal(result.weight_sum));
        }

        let coverage_val = if result.weight_sum > 1.0 {
            1.0
        } else {
            result.weight_sum
        };

        let return_coverage = PortfolioWeight::new(coverage_val)?;
        let observed_contribution = DecimalReturn::new(result.gross_return)?;

        Ok(Self {
            observed_contribution,
            return_coverage,
        })
    }

    /// Returns the observed gross decimal return contribution of the covered components.
    #[must_use]
    pub const fn observed_contribution(&self) -> DecimalReturn {
        self.observed_contribution
    }

    /// Returns the total weight of the components that contributed to this return.
    #[must_use]
    pub const fn return_coverage(&self) -> PortfolioWeight {
        self.return_coverage
    }

    /// Indicates whether the return coverage is equal to `1.0` within floating-point tolerance.
    #[must_use]
    pub fn has_full_coverage(&self) -> bool {
        (1.0 - self.return_coverage.value()).abs() <= WEIGHT_TOLERANCE
    }
}
