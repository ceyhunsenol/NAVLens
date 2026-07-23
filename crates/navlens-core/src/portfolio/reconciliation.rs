use crate::{CoreError, DecimalReturn, PortfolioReturnContribution};

/// Canonical result of reconciling a published fund return with its observed portfolio contribution.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct FundReturnReconciliation {
    published_fund_return: DecimalReturn,
    observed_portfolio_contribution: PortfolioReturnContribution,
    reconciliation_residual: DecimalReturn,
}

impl FundReturnReconciliation {
    /// Calculates the reconciliation residual between a published fund return and an observed portfolio contribution.
    ///
    /// The residual is defined as the difference between the published return and the observed covered contribution.
    ///
    /// # Errors
    /// Returns [`CoreError::NonFiniteNumber`] if the subtraction results in a non-finite floating point value.
    pub fn calculate(
        published_fund_return: DecimalReturn,
        observed_portfolio_contribution: PortfolioReturnContribution,
    ) -> Result<Self, CoreError> {
        let residual_value = published_fund_return.value()
            - observed_portfolio_contribution
                .observed_contribution()
                .value();

        let reconciliation_residual = DecimalReturn::new(residual_value)?;

        Ok(Self {
            published_fund_return,
            observed_portfolio_contribution,
            reconciliation_residual,
        })
    }

    /// The original published return of the fund.
    #[must_use]
    pub const fn published_fund_return(&self) -> DecimalReturn {
        self.published_fund_return
    }

    /// The aggregated return contribution of the covered portfolio components.
    #[must_use]
    pub const fn observed_portfolio_contribution(&self) -> PortfolioReturnContribution {
        self.observed_portfolio_contribution
    }

    /// The exact difference (`published_fund_return - observed_portfolio_contribution`).
    #[must_use]
    pub const fn reconciliation_residual(&self) -> DecimalReturn {
        self.reconciliation_residual
    }
}
