use crate::{MarketDate, PricingError};

/// Validates that a sequence of market dates contains at least two dates and is strictly chronological.
///
/// # Errors
/// Returns an error for too few observations, duplicate dates, or decreasing dates.
pub(super) fn validate_date_sequence<I>(dates: I) -> Result<(), PricingError>
where
    I: IntoIterator<Item = MarketDate>,
{
    let mut count = 0;
    let mut prev: Option<MarketDate> = None;
    for date in dates {
        count += 1;
        if let Some(previous) = prev {
            if date == previous {
                return Err(PricingError::DuplicatePriceDate(date));
            }
            if date < previous {
                return Err(PricingError::NonChronologicalPriceDate {
                    previous,
                    current: date,
                });
            }
        }
        prev = Some(date);
    }
    if count < 2 {
        return Err(PricingError::InsufficientPriceObservations(count));
    }
    Ok(())
}
