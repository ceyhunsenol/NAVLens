use navlens_core::FxRateKind;

/// Policy for matching and validating foreign exchange return boundaries.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FxReturnPolicy {
    required_fx_rate_kind: FxRateKind,
    max_fx_staleness_calendar_days: u32,
}

impl FxReturnPolicy {
    /// Creates a new `FxReturnPolicy`.
    #[must_use]
    pub const fn new(
        required_fx_rate_kind: FxRateKind,
        max_fx_staleness_calendar_days: u32,
    ) -> Self {
        Self {
            required_fx_rate_kind,
            max_fx_staleness_calendar_days,
        }
    }

    /// Returns the required FX rate kind.
    #[must_use]
    pub const fn required_fx_rate_kind(&self) -> FxRateKind {
        self.required_fx_rate_kind
    }

    /// Returns the maximum allowed staleness in calendar days.
    #[must_use]
    pub const fn max_fx_staleness_calendar_days(&self) -> u32 {
        self.max_fx_staleness_calendar_days
    }
}
