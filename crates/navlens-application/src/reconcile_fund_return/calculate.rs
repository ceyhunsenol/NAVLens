use super::error::ReconcileFundReturnError;
use super::result::FundReturnReconciliationResult;
use crate::ReturnContributionResult;
use navlens_calendar::PeriodDecimalReturn;
use navlens_core::FundReturnReconciliation;

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
    let published_period = published_fund_return.period();
    let contribution_period = *contribution_result.period();

    if published_period != contribution_period {
        return Err(ReconcileFundReturnError::PeriodMismatch {
            published_period,
            contribution_period,
        });
    }

    let core_result = FundReturnReconciliation::calculate(
        published_fund_return.decimal_return(),
        *contribution_result.observed_contribution(),
    )?;

    Ok(FundReturnReconciliationResult::new(
        published_period,
        core_result,
    ))
}
