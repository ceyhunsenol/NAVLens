use crate::calculate_fx_adjusted_return_contribution::FxBoundaryEvidence;
use navlens_calendar::MarketDate;
use navlens_core::{CurrencyPair, FxRateKind, HoldingPosition};

/// Reason why a covered holding could not provide a return for the target period.
#[derive(Clone, Debug, PartialEq)]
pub enum ReturnCoverageGapReason {
    MissingExactPeriodReturn,
    MissingDirectFxCandidate {
        required_pair: CurrencyPair,
        required_kind: FxRateKind,
    },
    FxRateKindMismatch {
        required_pair: CurrencyPair,
        required_kind: FxRateKind,
        available_kinds: Vec<FxRateKind>,
    },
    MissingFxStartObservation {
        required_pair: CurrencyPair,
        required_kind: FxRateKind,
        requested_date: MarketDate,
    },
    StaleFxStartObservation {
        evidence: FxBoundaryEvidence,
        maximum_staleness_calendar_days: u32,
    },
    StaleFxEndObservation {
        evidence: FxBoundaryEvidence,
        maximum_staleness_calendar_days: u32,
    },
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
