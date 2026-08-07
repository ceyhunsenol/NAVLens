use super::evidence::CurrencyReturnAdjustment;
use crate::return_coverage_breakdown::ReturnCoverageBreakdown;
use navlens_calendar::{PeriodDecimalReturn, ReturnPeriod};
use navlens_core::{
    DecimalReturn, HoldingPosition, PortfolioComponentContribution, PortfolioReturnContribution,
};

/// The calculated FX-adjusted return contribution for a single covered holding.
#[derive(Clone, Debug, PartialEq)]
pub struct FxAdjustedComponentContribution {
    holding: HoldingPosition,
    security_period_return: PeriodDecimalReturn,
    currency_adjustment: CurrencyReturnAdjustment,
    effective_base_currency_return: DecimalReturn,
    contribution: PortfolioComponentContribution,
}

impl FxAdjustedComponentContribution {
    /// Creates a new `FxAdjustedComponentContribution`.
    #[must_use]
    pub(crate) const fn new(
        holding: HoldingPosition,
        security_period_return: PeriodDecimalReturn,
        currency_adjustment: CurrencyReturnAdjustment,
        effective_base_currency_return: DecimalReturn,
        contribution: PortfolioComponentContribution,
    ) -> Self {
        Self {
            holding,
            security_period_return,
            currency_adjustment,
            effective_base_currency_return,
            contribution,
        }
    }

    /// Returns the holding position.
    #[must_use]
    pub const fn holding(&self) -> &HoldingPosition {
        &self.holding
    }

    /// Returns the exact-period security return in its original currency.
    #[must_use]
    pub const fn security_period_return(&self) -> &PeriodDecimalReturn {
        &self.security_period_return
    }

    /// Returns the applied currency return adjustment, if any.
    #[must_use]
    pub const fn currency_adjustment(&self) -> &CurrencyReturnAdjustment {
        &self.currency_adjustment
    }

    /// Returns the effective decimal return after FX adjustments.
    #[must_use]
    pub const fn effective_base_currency_return(&self) -> &DecimalReturn {
        &self.effective_base_currency_return
    }

    /// Returns the final calculated portfolio component contribution.
    #[must_use]
    pub const fn contribution(&self) -> &PortfolioComponentContribution {
        &self.contribution
    }
}

/// The result of calculating the FX-adjusted portfolio return contribution.
#[derive(Clone, Debug, PartialEq)]
pub struct FxAdjustedReturnContributionResult {
    period: ReturnPeriod,
    component_contributions: Vec<FxAdjustedComponentContribution>,
    observed_contribution: PortfolioReturnContribution,
    breakdown: ReturnCoverageBreakdown,
}

impl FxAdjustedReturnContributionResult {
    /// Creates a new `FxAdjustedReturnContributionResult`.
    #[must_use]
    pub(crate) const fn new(
        period: ReturnPeriod,
        component_contributions: Vec<FxAdjustedComponentContribution>,
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

    /// Returns the calculated FX-adjusted contributions of each covered component.
    #[must_use]
    pub fn component_contributions(&self) -> &[FxAdjustedComponentContribution] {
        &self.component_contributions
    }

    /// Returns the mathematically sound sum of the component contributions.
    #[must_use]
    pub const fn observed_contribution(&self) -> &PortfolioReturnContribution {
        &self.observed_contribution
    }

    /// Returns the original price coverage weight of the portfolio.
    #[must_use]
    pub const fn price_coverage(&self) -> &navlens_core::PortfolioWeight {
        self.breakdown.price_coverage()
    }

    /// Returns the list of holdings that had no price coverage.
    #[must_use]
    pub fn price_gaps(&self) -> &[crate::align_holdings_prices::UncoveredHolding] {
        self.breakdown.price_gaps()
    }

    /// Returns the list of holdings that had price coverage but failed to provide an exact period return.
    #[must_use]
    pub fn return_gaps(&self) -> &[crate::calculate_return_contribution::ReturnCoverageGap] {
        self.breakdown.return_gaps()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use navlens_calendar::MarketDate;
    use navlens_core::{AssetClass, InstrumentId, PortfolioComponent, PortfolioWeight};

    #[test]
    fn preserves_component_getters() {
        let holding = HoldingPosition::new(
            InstrumentId::new("INST").unwrap(),
            AssetClass::Equity,
            PortfolioWeight::new(0.5).unwrap(),
        );
        let sec_ret = PeriodDecimalReturn::new(
            MarketDate::new(2026, 1, 1).unwrap(),
            MarketDate::new(2026, 1, 31).unwrap(),
            DecimalReturn::new(0.1).unwrap(),
        )
        .unwrap();
        let eff_ret = DecimalReturn::new(0.1).unwrap();
        let comp = PortfolioComponent {
            weight: holding.fund_total_weight(),
            market_return: eff_ret,
        };
        let contrib = PortfolioComponentContribution::calculate(&comp).unwrap();

        let adjusted = FxAdjustedComponentContribution {
            holding: holding.clone(),
            security_period_return: sec_ret,
            currency_adjustment: CurrencyReturnAdjustment::NotRequired,
            effective_base_currency_return: eff_ret,
            contribution: contrib,
        };

        assert_eq!(adjusted.holding(), &holding);
        assert_eq!(adjusted.security_period_return(), &sec_ret);
        assert_eq!(
            adjusted.currency_adjustment(),
            &CurrencyReturnAdjustment::NotRequired
        );
        assert_eq!(adjusted.effective_base_currency_return(), &eff_ret);
        assert_eq!(adjusted.contribution(), &contrib);
    }

    #[test]
    fn preserves_result_coverage_getters() {
        let breakdown =
            ReturnCoverageBreakdown::new(PortfolioWeight::new(0.8).unwrap(), vec![], vec![]);
        let period = ReturnPeriod::new(
            MarketDate::new(2026, 1, 1).unwrap(),
            MarketDate::new(2026, 1, 31).unwrap(),
        )
        .unwrap();

        let result = FxAdjustedReturnContributionResult {
            period,
            component_contributions: vec![],
            observed_contribution: PortfolioReturnContribution::calculate(&[]).unwrap(),
            breakdown,
        };

        assert_eq!(result.period(), &period);
        assert_eq!(result.component_contributions().len(), 0);
        assert_eq!(
            result.observed_contribution(),
            &PortfolioReturnContribution::calculate(&[]).unwrap()
        );
        assert_eq!(result.price_coverage(), &PortfolioWeight::new(0.8).unwrap());
        assert_eq!(result.price_gaps().len(), 0);
        assert_eq!(result.return_gaps().len(), 0);
    }
}
