use crate::CalendarError;
use std::fmt::{Display, Formatter};
use time::{Date, Month, Weekday};

/// A Gregorian civil date used by a market calendar.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct MarketDate(Date);

impl MarketDate {
    /// Creates a validated Gregorian market date.
    ///
    /// # Errors
    /// Returns [`CalendarError::InvalidDate`] when the components do not form a
    /// valid Gregorian date.
    pub fn new(year: i32, month: u8, day: u8) -> Result<Self, CalendarError> {
        let month =
            Month::try_from(month).map_err(|_| CalendarError::InvalidDate { year, month, day })?;
        let date =
            Date::from_calendar_date(year, month, day).map_err(|_| CalendarError::InvalidDate {
                year,
                month: u8::from(month),
                day,
            })?;

        Ok(Self(date))
    }

    /// Calculates the number of calendar days elapsed since `earlier`.
    ///
    /// # Sign Semantics
    /// - Positive (`> 0`) if `self` is chronologically later than `earlier`.
    /// - Zero (`0`) if `self` is on the exact same date as `earlier`.
    /// - Negative (`< 0`) if `self` is chronologically earlier than `earlier`.
    #[must_use]
    pub fn calendar_days_since(self, earlier: Self) -> i64 {
        (self.0 - earlier.0).whole_days()
    }

    pub(crate) const fn weekday(self) -> Weekday {
        self.0.weekday()
    }

    pub(crate) const fn next_day(self) -> Option<Self> {
        match self.0.next_day() {
            Some(date) => Some(Self(date)),
            None => None,
        }
    }
}

impl Display for MarketDate {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        Display::fmt(&self.0, formatter)
    }
}
