use crate::{CalendarError, MarketDate, SessionKind, SessionOverride};
use std::collections::BTreeMap;
use time::Weekday;

/// A deterministic session calendar with explicit date overrides.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct MarketCalendar {
    overrides: BTreeMap<MarketDate, SessionKind>,
}

impl MarketCalendar {
    /// Creates a calendar and rejects conflicting duplicate dates.
    ///
    /// # Errors
    /// Returns [`CalendarError::DuplicateSessionDate`] when more than one
    /// override targets the same date.
    pub fn new(overrides: &[SessionOverride]) -> Result<Self, CalendarError> {
        let mut sessions = BTreeMap::new();

        for session_override in overrides {
            if sessions
                .insert(session_override.date(), session_override.session())
                .is_some()
            {
                return Err(CalendarError::DuplicateSessionDate(session_override.date()));
            }
        }

        Ok(Self {
            overrides: sessions,
        })
    }

    #[must_use]
    pub fn session_on(&self, date: MarketDate) -> SessionKind {
        self.overrides.get(&date).copied().unwrap_or_else(|| {
            if matches!(date.weekday(), Weekday::Saturday | Weekday::Sunday) {
                SessionKind::Closed
            } else {
                SessionKind::FullDay
            }
        })
    }

    /// Returns the first open session strictly after `date`.
    ///
    /// # Errors
    /// Returns [`CalendarError::NoFutureOpenDate`] at the representable date
    /// boundary when no later date can be inspected.
    pub fn next_open_date(&self, date: MarketDate) -> Result<MarketDate, CalendarError> {
        let mut candidate = date.next_day().ok_or(CalendarError::NoFutureOpenDate)?;

        loop {
            if self.session_on(candidate).is_open() {
                return Ok(candidate);
            }
            candidate = candidate
                .next_day()
                .ok_or(CalendarError::NoFutureOpenDate)?;
        }
    }
}
