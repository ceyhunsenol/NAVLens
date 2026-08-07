use crate::align_holdings_prices::UncoveredHolding;
use crate::calculate_return_contribution::ReturnCoverageGap;
use navlens_core::PortfolioWeight;

/// Internal grouping of the coverage breakdown metrics.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct ReturnCoverageBreakdown {
    price_coverage: PortfolioWeight,
    price_gaps: Vec<UncoveredHolding>,
    return_gaps: Vec<ReturnCoverageGap>,
}

impl ReturnCoverageBreakdown {
    pub(crate) const fn new(
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

    pub(crate) const fn price_coverage(&self) -> &PortfolioWeight {
        &self.price_coverage
    }

    pub(crate) fn price_gaps(&self) -> &[UncoveredHolding] {
        &self.price_gaps
    }

    pub(crate) fn return_gaps(&self) -> &[ReturnCoverageGap] {
        &self.return_gaps
    }
}
