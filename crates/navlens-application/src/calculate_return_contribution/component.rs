use navlens_calendar::PeriodDecimalReturn;
use navlens_core::{HoldingPosition, PortfolioComponentContribution};

/// A portfolio component mapped to its exact period return and calculated contribution.
#[derive(Clone, Debug, PartialEq)]
pub struct ComponentContribution {
    holding: HoldingPosition,
    period_return: PeriodDecimalReturn,
    contribution: PortfolioComponentContribution,
}

impl ComponentContribution {
    /// Creates a new `ComponentContribution`.
    #[must_use]
    pub(crate) const fn new(
        holding: HoldingPosition,
        period_return: PeriodDecimalReturn,
        contribution: PortfolioComponentContribution,
    ) -> Self {
        Self {
            holding,
            period_return,
            contribution,
        }
    }

    /// Returns the holding position.
    #[must_use]
    pub const fn holding(&self) -> &HoldingPosition {
        &self.holding
    }

    /// Returns the matched period decimal return.
    #[must_use]
    pub const fn period_return(&self) -> &PeriodDecimalReturn {
        &self.period_return
    }

    /// Returns the canonical component contribution calculation.
    #[must_use]
    pub const fn contribution(&self) -> &PortfolioComponentContribution {
        &self.contribution
    }
}
