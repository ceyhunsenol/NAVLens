use crate::{DatedDecimalReturn, MarketDate, PeriodDecimalReturn, PricingError};
use navlens_core::{UnitPrice, calculate_decimal_return};

/// Calculates period decimal returns across consecutive price observations.
pub(super) fn calculate_period_decimal_returns<T, F>(
    observations: &[T],
    extract: F,
) -> Result<Vec<PeriodDecimalReturn>, PricingError>
where
    F: Fn(&T) -> (MarketDate, UnitPrice),
{
    observations
        .windows(2)
        .map(|pair| {
            let (start_date, prev_price) = extract(&pair[0]);
            let (end_date, curr_price) = extract(&pair[1]);
            let decimal_return = calculate_decimal_return(prev_price, curr_price)
                .map_err(PricingError::ReturnCalculation)?;
            PeriodDecimalReturn::new(start_date, end_date, decimal_return)
        })
        .collect()
}

/// Calculates dated decimal returns across consecutive price observations by delegating
/// to the canonical period return calculation.
pub(super) fn calculate_dated_decimal_returns<T, F>(
    observations: &[T],
    extract: F,
) -> Result<Vec<DatedDecimalReturn>, PricingError>
where
    F: Fn(&T) -> (MarketDate, UnitPrice),
{
    let period_returns = calculate_period_decimal_returns(observations, extract)?;
    Ok(period_returns
        .into_iter()
        .map(|period_return| {
            DatedDecimalReturn::new(
                period_return.period_end_date(),
                period_return.decimal_return(),
            )
        })
        .collect())
}
