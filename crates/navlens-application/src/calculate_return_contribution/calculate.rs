use super::aggregate::calculate_aggregate_contribution;
use super::breakdown::construct_return_coverage_breakdown;
use super::component::ComponentContribution;
use super::contribution::calculate_canonical_contribution;
use super::error::CalculateReturnContributionError;
use super::exact_period::match_exact_period_return;
use super::gap::{ReturnCoverageGap, ReturnCoverageGapReason};
use super::result::ReturnContributionResult;
use crate::align_holdings_prices::PortfolioCoverageReport;
use navlens_calendar::ReturnPeriod;

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
        if let Some(pr) = match_exact_period_return(covered, target_period)? {
            let (pc, contribution) = calculate_canonical_contribution(
                covered.holding().fund_total_weight(),
                pr.decimal_return(),
            )?;
            portfolio_components.push(pc);
            component_contributions.push(ComponentContribution::new(
                covered.holding().clone(),
                pr,
                contribution,
            ));
        } else {
            return_gaps.push(ReturnCoverageGap::new(
                covered.holding().clone(),
                ReturnCoverageGapReason::MissingExactPeriodReturn,
            ));
        }
    }

    let observed_contribution = calculate_aggregate_contribution(&portfolio_components)?;
    let breakdown = construct_return_coverage_breakdown(report, return_gaps);

    Ok(ReturnContributionResult::new(
        target_period,
        component_contributions,
        observed_contribution,
        breakdown,
    ))
}
