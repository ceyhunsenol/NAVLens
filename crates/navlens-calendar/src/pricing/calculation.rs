use crate::{DatedDecimalReturn, MarketDate, PricingError};
use navlens_core::{UnitPrice, calculate_decimal_return};

/// Calculates dated decimal returns across consecutive price observations.
pub(super) fn calculate_dated_decimal_returns<T, F>(
    observations: &[T],
    extract: F,
) -> Result<Vec<DatedDecimalReturn>, PricingError>
where
    F: Fn(&T) -> (MarketDate, UnitPrice),
{
    observations
        .windows(2)
        .map(|pair| {
            let (_, prev_price) = extract(&pair[0]);
            let (curr_date, curr_price) = extract(&pair[1]);
            calculate_decimal_return(prev_price, curr_price)
                .map(|value| DatedDecimalReturn::new(curr_date, value))
                .map_err(PricingError::ReturnCalculation)
        })
        .collect()
}
