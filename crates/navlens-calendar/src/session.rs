use crate::MarketDate;

/// Trading or valuation availability for one market date.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SessionKind {
    FullDay,
    HalfDay,
    Closed,
}

impl SessionKind {
    #[must_use]
    pub const fn is_open(self) -> bool {
        !matches!(self, Self::Closed)
    }
}

/// An authoritative replacement for a calendar's default weekday rule.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SessionOverride {
    date: MarketDate,
    session: SessionKind,
}

impl SessionOverride {
    #[must_use]
    pub const fn new(date: MarketDate, session: SessionKind) -> Self {
        Self { date, session }
    }

    #[must_use]
    pub const fn date(self) -> MarketDate {
        self.date
    }

    #[must_use]
    pub const fn session(self) -> SessionKind {
        self.session
    }
}
