use crate::{MarketDate, PricingError};

#[derive(Clone, Debug, PartialEq)]
pub(super) enum DateSequenceViolation {
    Duplicate(MarketDate),
    NonChronological {
        previous: MarketDate,
        current: MarketDate,
    },
}

pub(super) fn validate_strict_date_order<I>(dates: I) -> Result<usize, DateSequenceViolation>
where
    I: IntoIterator<Item = MarketDate>,
{
    let mut count = 0;
    let mut prev: Option<MarketDate> = None;
    for date in dates {
        count += 1;
        if let Some(previous) = prev {
            if date == previous {
                return Err(DateSequenceViolation::Duplicate(date));
            }
            if date < previous {
                return Err(DateSequenceViolation::NonChronological {
                    previous,
                    current: date,
                });
            }
        }
        prev = Some(date);
    }
    Ok(count)
}

/// Validates that a sequence of market dates contains at least two dates and is strictly chronological.
///
/// # Errors
/// Returns an error for too few observations, duplicate dates, or decreasing dates.
pub(super) fn validate_date_sequence<I>(dates: I) -> Result<(), PricingError>
where
    I: IntoIterator<Item = MarketDate>,
{
    match validate_strict_date_order(dates) {
        Ok(count) => {
            if count < 2 {
                Err(PricingError::InsufficientPriceObservations(count))
            } else {
                Ok(())
            }
        }
        Err(DateSequenceViolation::Duplicate(date)) => Err(PricingError::DuplicatePriceDate(date)),
        Err(DateSequenceViolation::NonChronological { previous, current }) => {
            Err(PricingError::NonChronologicalPriceDate { previous, current })
        }
    }
}
