use super::component::ComponentContribution;
use super::error::CalculateReturnContributionError;
use super::gap::{ReturnCoverageGap, ReturnCoverageGapReason};
use super::result::{ReturnContributionResult, ReturnCoverageBreakdown};
use crate::align_holdings_prices::{CoveredHoldingPrice, PortfolioCoverageReport};
use navlens_calendar::ReturnPeriod;
use navlens_core::{
    PortfolioComponent, PortfolioComponentContribution, PortfolioReturnContribution,
};

/// Matches an exact period return for a single covered holding.
fn match_exact_period_return(
    covered: &CoveredHoldingPrice,
    target_period: ReturnPeriod,
) -> Result<Option<ComponentContribution>, CalculateReturnContributionError> {
    let period_returns = covered.series().period_returns()?;
    let exact_return = period_returns
        .into_iter()
        .find(|pr| pr.period() == target_period);

    if let Some(pr) = exact_return {
        let component = PortfolioComponent {
            weight: covered.holding().fund_total_weight(),
            market_return: pr.decimal_return(),
        };
        let contribution = PortfolioComponentContribution::calculate(&component)?;
        Ok(Some(ComponentContribution::new(
            covered.holding().clone(),
            pr,
            contribution,
        )))
    } else {
        Ok(None)
    }
}

/// Calculates the exact-period aligned portfolio return contribution.
///
/// # Errors
/// Returns an error if any canonical domain calculations fail.
pub fn calculate_return_contribution(
    report: &PortfolioCoverageReport,
    target_period: ReturnPeriod,
) -> Result<ReturnContributionResult, CalculateReturnContributionError> {
    let mut component_contributions = Vec::new();
    let mut return_gaps = Vec::new();
    let mut portfolio_components = Vec::new();

    for covered in report.covered() {
        if let Some(component) = match_exact_period_return(covered, target_period)? {
            portfolio_components.push(PortfolioComponent {
                weight: component.holding().fund_total_weight(),
                market_return: component.period_return().decimal_return(),
            });
            component_contributions.push(component);
        } else {
            return_gaps.push(ReturnCoverageGap::new(
                covered.holding().clone(),
                ReturnCoverageGapReason::MissingExactPeriodReturn,
            ));
        }
    }

    let observed_contribution = PortfolioReturnContribution::calculate(&portfolio_components)?;
    let breakdown = ReturnCoverageBreakdown::new(
        report.weights().covered_weight(),
        report.uncovered_listed().to_vec(),
        return_gaps,
    );

    Ok(ReturnContributionResult::new(
        target_period,
        component_contributions,
        observed_contribution,
        breakdown,
    ))
}
