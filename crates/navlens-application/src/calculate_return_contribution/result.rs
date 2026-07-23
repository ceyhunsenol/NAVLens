use super::component::ComponentContribution;
use super::gap::ReturnCoverageGap;
use crate::align_holdings_prices::UncoveredHolding;
use navlens_calendar::ReturnPeriod;
use navlens_core::{PortfolioReturnContribution, PortfolioWeight};

/// Internal grouping of the coverage breakdown metrics.
#[derive(Clone, Debug, PartialEq)]
pub(super) struct ReturnCoverageBreakdown {
    price_coverage: PortfolioWeight,
    price_gaps: Vec<UncoveredHolding>,
    return_gaps: Vec<ReturnCoverageGap>,
}

impl ReturnCoverageBreakdown {
    pub(super) const fn new(
        price_coverage: PortfolioWeight,
        price_gaps: Vec<UncoveredHolding>,
        return_gaps: Vec<ReturnCoverageGap>,
    ) -> Self {
        Self {
            price_coverage,
            price_gaps,
            return_gaps,
        }
    }
}

/// The result of calculating the aligned portfolio return contribution.
#[derive(Clone, Debug, PartialEq)]
pub struct ReturnContributionResult {
    period: ReturnPeriod,
    component_contributions: Vec<ComponentContribution>,
    observed_contribution: PortfolioReturnContribution,
    breakdown: ReturnCoverageBreakdown,
}

impl ReturnContributionResult {
    /// Creates a new `ReturnContributionResult`.
    #[must_use]
    pub(super) const fn new(
        period: ReturnPeriod,
        component_contributions: Vec<ComponentContribution>,
        observed_contribution: PortfolioReturnContribution,
        breakdown: ReturnCoverageBreakdown,
    ) -> Self {
        Self {
            period,
            component_contributions,
            observed_contribution,
            breakdown,
        }
    }

    /// Returns the target return period.
    #[must_use]
    pub const fn period(&self) -> &ReturnPeriod {
        &self.period
    }

    /// Returns the calculated contributions of each covered component.
    #[must_use]
    pub fn component_contributions(&self) -> &[ComponentContribution] {
        &self.component_contributions
    }

    /// Returns the mathematically sound sum of the component contributions.
    #[must_use]
    pub const fn observed_contribution(&self) -> &PortfolioReturnContribution {
        &self.observed_contribution
    }

    /// Returns the original price coverage weight of the portfolio.
    #[must_use]
    pub const fn price_coverage(&self) -> &PortfolioWeight {
        &self.breakdown.price_coverage
    }

    /// Returns the list of holdings that had no price coverage.
    #[must_use]
    pub fn price_gaps(&self) -> &[UncoveredHolding] {
        &self.breakdown.price_gaps
    }

    /// Returns the list of holdings that had price coverage but failed to provide an exact period return.
    #[must_use]
    pub fn return_gaps(&self) -> &[ReturnCoverageGap] {
        &self.breakdown.return_gaps
    }
}
