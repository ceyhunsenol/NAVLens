use navlens_core::HoldingPosition;

/// Reason why a covered holding could not provide a return for the target period.
#[derive(Clone, Debug, PartialEq)]
pub enum ReturnCoverageGapReason {
    MissingExactPeriodReturn,
}

/// A holding that had price coverage but failed to provide an exact period return.
#[derive(Clone, Debug, PartialEq)]
pub struct ReturnCoverageGap {
    holding: HoldingPosition,
    reason: ReturnCoverageGapReason,
}

impl ReturnCoverageGap {
    /// Creates a new `ReturnCoverageGap`.
    #[must_use]
    pub(crate) const fn new(holding: HoldingPosition, reason: ReturnCoverageGapReason) -> Self {
        Self { holding, reason }
    }

    /// Returns the holding position.
    #[must_use]
    pub const fn holding(&self) -> &HoldingPosition {
        &self.holding
    }

    /// Returns the reason why this holding failed to provide a return.
    #[must_use]
    pub const fn reason(&self) -> &ReturnCoverageGapReason {
        &self.reason
    }
}
