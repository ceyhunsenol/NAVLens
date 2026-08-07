use super::boundary::{select_end_boundary, select_start_boundary};
use super::candidates::FxCandidateIndex;
use super::{
    CurrencyReturnAdjustment, FxAdjustedComponentContribution, FxAdjustedReturnContributionResult,
    FxAdjustmentEvidence, FxReturnPolicy,
};
use crate::align_holdings_prices::{CoveredHoldingPrice, PortfolioCoverageReport};
use crate::calculate_return_contribution::{
    CalculateReturnContributionError, ReturnCoverageGap, ReturnCoverageGapReason,
    calculate_aggregate_contribution, calculate_canonical_contribution,
    construct_return_coverage_breakdown, match_exact_period_return,
};
use navlens_calendar::{FxRateSeries, PeriodDecimalReturn, ReturnPeriod};
use navlens_core::{
    CurrencyCode, CurrencyPair, FxAdjustedPeriodReturn, PortfolioComponent,
    calculate_fx_decimal_return,
};

type GapOr<T> = Result<T, ReturnCoverageGapReason>;

struct FxCalculationContext<'a> {
    target_period: ReturnPeriod,
    candidates: &'a FxCandidateIndex<'a>,
    policy: &'a FxReturnPolicy,
    base_currency: &'a CurrencyCode,
}

enum ComponentOutcome {
    Contributed {
        aggregate_component: PortfolioComponent,
        result: FxAdjustedComponentContribution,
    },
    Gap(ReturnCoverageGap),
}

fn required_fx_series<'a>(
    context: &'a FxCalculationContext<'a>,
    pair: &CurrencyPair,
) -> GapOr<&'a FxRateSeries> {
    let required_kind = context.policy.required_fx_rate_kind();
    if let Some(series) = context.candidates.get(pair, required_kind) {
        return Ok(series);
    }
    let available_kinds = context.candidates.available_kinds(pair);
    if available_kinds.is_empty() {
        return Err(ReturnCoverageGapReason::MissingDirectFxCandidate {
            required_pair: pair.clone(),
            required_kind,
        });
    }
    Err(ReturnCoverageGapReason::FxRateKindMismatch {
        required_pair: pair.clone(),
        required_kind,
        available_kinds,
    })
}

fn calculate_adjustment(
    context: &FxCalculationContext<'_>,
    pair: &CurrencyPair,
) -> Result<GapOr<FxAdjustmentEvidence>, CalculateReturnContributionError> {
    let kind = context.policy.required_fx_rate_kind();
    let series = match required_fx_series(context, pair) {
        Ok(series) => series,
        Err(reason) => return Ok(Err(reason)),
    };
    let start = match select_start_boundary(
        series,
        context.target_period.period_start_date(),
        *context.policy,
        pair,
        kind,
    )? {
        Ok(evidence) => evidence,
        Err(reason) => return Ok(Err(reason)),
    };
    let end = match select_end_boundary(
        series,
        context.target_period.period_end_date(),
        *context.policy,
    )? {
        Ok(evidence) => evidence,
        Err(reason) => return Ok(Err(reason)),
    };
    let fx_return =
        calculate_fx_decimal_return(start.observation().rate(), end.observation().rate())?;
    Ok(Ok(FxAdjustmentEvidence::new(start, end, fx_return)?))
}

fn contributed_component(
    covered: &CoveredHoldingPrice,
    security_return: PeriodDecimalReturn,
    adjustment: CurrencyReturnAdjustment,
    effective_return: navlens_core::DecimalReturn,
) -> Result<ComponentOutcome, CalculateReturnContributionError> {
    let (aggregate_component, contribution) =
        calculate_canonical_contribution(covered.holding().fund_total_weight(), effective_return)?;
    let result = FxAdjustedComponentContribution::new(
        covered.holding().clone(),
        security_return,
        adjustment,
        effective_return,
        contribution,
    );
    Ok(ComponentOutcome::Contributed {
        aggregate_component,
        result,
    })
}

fn calculate_foreign_component(
    covered: &CoveredHoldingPrice,
    security_return: PeriodDecimalReturn,
    context: &FxCalculationContext<'_>,
) -> Result<ComponentOutcome, CalculateReturnContributionError> {
    let pair = CurrencyPair::new(
        covered.series().currency().clone(),
        context.base_currency.clone(),
    )?;
    let adjustment = match calculate_adjustment(context, &pair)? {
        Ok(adjustment) => adjustment,
        Err(reason) => {
            return Ok(ComponentOutcome::Gap(ReturnCoverageGap::new(
                covered.holding().clone(),
                reason,
            )));
        }
    };
    let effective_return = FxAdjustedPeriodReturn::calculate(
        security_return.decimal_return(),
        adjustment.fx_return(),
    )?
    .decimal_return();
    contributed_component(
        covered,
        security_return,
        CurrencyReturnAdjustment::Applied(adjustment),
        effective_return,
    )
}

fn calculate_component(
    covered: &CoveredHoldingPrice,
    context: &FxCalculationContext<'_>,
) -> Result<ComponentOutcome, CalculateReturnContributionError> {
    let Some(security_return) = match_exact_period_return(covered, context.target_period)? else {
        return Ok(ComponentOutcome::Gap(ReturnCoverageGap::new(
            covered.holding().clone(),
            ReturnCoverageGapReason::MissingExactPeriodReturn,
        )));
    };
    if covered.series().currency() == context.base_currency {
        return contributed_component(
            covered,
            security_return,
            CurrencyReturnAdjustment::NotRequired,
            security_return.decimal_return(),
        );
    }
    calculate_foreign_component(covered, security_return, context)
}

/// Calculates the FX-adjusted portfolio return contribution.
///
/// # Errors
/// Returns an error when candidate identity or canonical calculations fail.
pub fn calculate_fx_adjusted_return_contribution(
    report: &PortfolioCoverageReport,
    target_period: ReturnPeriod,
    fx_candidates: &[FxRateSeries],
    fx_policy: &FxReturnPolicy,
) -> Result<FxAdjustedReturnContributionResult, CalculateReturnContributionError> {
    let candidates = FxCandidateIndex::new(fx_candidates)?;
    let context = FxCalculationContext {
        target_period,
        candidates: &candidates,
        policy: fx_policy,
        base_currency: report.policy().fund_base_currency(),
    };
    let mut results = Vec::new();
    let mut gaps = Vec::new();
    let mut aggregate_components = Vec::new();
    for covered in report.covered() {
        match calculate_component(covered, &context)? {
            ComponentOutcome::Contributed {
                aggregate_component,
                result,
            } => {
                aggregate_components.push(aggregate_component);
                results.push(result);
            }
            ComponentOutcome::Gap(gap) => gaps.push(gap),
        }
    }
    let observed = calculate_aggregate_contribution(&aggregate_components)?;
    let breakdown = construct_return_coverage_breakdown(report, gaps);
    Ok(FxAdjustedReturnContributionResult::new(
        target_period,
        results,
        observed,
        breakdown,
    ))
}
