use super::error::ReconcileFundReturnError;
use super::result::FundReturnReconciliationResult;
use crate::{FxAdjustedReturnContributionResult, ReturnContributionResult};
use navlens_calendar::{PeriodDecimalReturn, ReturnPeriod};
use navlens_core::{FundReturnReconciliation, PortfolioReturnContribution};

fn reconcile_canonical_fund_return(
    published_fund_return: PeriodDecimalReturn,
    contribution_period: ReturnPeriod,
    observed_contribution: PortfolioReturnContribution,
) -> Result<FundReturnReconciliationResult, ReconcileFundReturnError> {
    let published_period = published_fund_return.period();

    if published_period != contribution_period {
        return Err(ReconcileFundReturnError::PeriodMismatch {
            published_period,
            contribution_period,
        });
    }

    let core_result = FundReturnReconciliation::calculate(
        published_fund_return.decimal_return(),
        observed_contribution,
    )?;

    Ok(FundReturnReconciliationResult::new(
        published_period,
        core_result,
    ))
}

/// Orchestrates the exact-period alignment and calculation of fund return reconciliation.
///
/// # Errors
/// Returns [`ReconcileFundReturnError::PeriodMismatch`] if the periods of the published return and the
/// observed contribution are not exactly equal.
/// Returns [`ReconcileFundReturnError::Domain`] if the subtraction produces a non-finite float.
pub fn reconcile_fund_return(
    published_fund_return: PeriodDecimalReturn,
    contribution_result: &ReturnContributionResult,
) -> Result<FundReturnReconciliationResult, ReconcileFundReturnError> {
    reconcile_canonical_fund_return(
        published_fund_return,
        *contribution_result.period(),
        *contribution_result.observed_contribution(),
    )
}

/// Orchestrates the exact-period alignment and calculation of FX-adjusted fund return reconciliation.
///
/// # Errors
/// Returns [`ReconcileFundReturnError::PeriodMismatch`] if the periods of the published return and the
/// observed contribution are not exactly equal.
/// Returns [`ReconcileFundReturnError::Domain`] if the subtraction produces a non-finite float.
pub fn reconcile_fx_adjusted_fund_return(
    published_fund_return: PeriodDecimalReturn,
    contribution_result: &FxAdjustedReturnContributionResult,
) -> Result<FundReturnReconciliationResult, ReconcileFundReturnError> {
    reconcile_canonical_fund_return(
        published_fund_return,
        *contribution_result.period(),
        *contribution_result.observed_contribution(),
    )
}
