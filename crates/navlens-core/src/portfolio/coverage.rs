use crate::{CoreError, PortfolioWeight};

/// Accounting breakdown of covered, uncovered listed, and unrepresented fund portfolio weights.
#[allow(clippy::struct_field_names)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PortfolioCoverageWeights {
    declared_weight: PortfolioWeight,
    covered_weight: PortfolioWeight,
    uncovered_listed_weight: PortfolioWeight,
    unrepresented_weight: PortfolioWeight,
    total_uncovered_weight: PortfolioWeight,
}

impl PortfolioCoverageWeights {
    /// Calculates portfolio coverage weights from covered and uncovered listed weights.
    ///
    /// # Errors
    /// Returns `CoreError::DeclaredWeightExceedsFundTotal` if the sum of covered and
    /// uncovered listed weights exceeds `1.0`.
    pub fn new(
        covered_weights: &[PortfolioWeight],
        uncovered_listed_weights: &[PortfolioWeight],
    ) -> Result<Self, CoreError> {
        let covered_val: f64 = covered_weights.iter().map(|w| w.value()).sum();
        let uncovered_listed_val: f64 = uncovered_listed_weights.iter().map(|w| w.value()).sum();
        let declared_val = covered_val + uncovered_listed_val;

        if declared_val > 1.0 {
            return Err(CoreError::DeclaredWeightExceedsFundTotal(declared_val));
        }

        let unrepresented_val = 1.0 - declared_val;
        let total_uncovered_val = uncovered_listed_val + unrepresented_val;

        Ok(Self {
            declared_weight: PortfolioWeight::new(declared_val)?,
            covered_weight: PortfolioWeight::new(covered_val)?,
            uncovered_listed_weight: PortfolioWeight::new(uncovered_listed_val)?,
            unrepresented_weight: PortfolioWeight::new(unrepresented_val)?,
            total_uncovered_weight: PortfolioWeight::new(total_uncovered_val)?,
        })
    }

    /// Sum of all positions declared in the holdings snapshot (`covered + uncovered_listed`).
    #[must_use]
    pub const fn declared_weight(&self) -> PortfolioWeight {
        self.declared_weight
    }

    /// Sum of positions with an accepted aligned price series.
    #[must_use]
    pub const fn covered_weight(&self) -> PortfolioWeight {
        self.covered_weight
    }

    /// Sum of listed positions with a coverage gap.
    #[must_use]
    pub const fn uncovered_listed_weight(&self) -> PortfolioWeight {
        self.uncovered_listed_weight
    }

    /// Weight not represented in the holdings snapshot (`1.0 - declared`).
    #[must_use]
    pub const fn unrepresented_weight(&self) -> PortfolioWeight {
        self.unrepresented_weight
    }

    /// Total weight not covered (`uncovered_listed + unrepresented`).
    #[must_use]
    pub const fn total_uncovered_weight(&self) -> PortfolioWeight {
        self.total_uncovered_weight
    }

    /// Returns the coverage ratio, which equals `covered_weight`.
    #[must_use]
    pub const fn coverage_ratio(&self) -> PortfolioWeight {
        self.covered_weight
    }
}
