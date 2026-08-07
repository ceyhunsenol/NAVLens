use crate::align_holdings_prices::CoveredHoldingPrice;
use crate::calculate_return_contribution::CalculateReturnContributionError;
use navlens_calendar::{PeriodDecimalReturn, ReturnPeriod};

/// Matches an exact period return for a single covered holding.
pub(crate) fn match_exact_period_return(
    covered: &CoveredHoldingPrice,
    target_period: ReturnPeriod,
) -> Result<Option<PeriodDecimalReturn>, CalculateReturnContributionError> {
    let period_returns = covered.series().period_returns()?;
    let exact_return = period_returns
        .into_iter()
        .find(|pr| pr.period() == target_period);
    Ok(exact_return)
}
