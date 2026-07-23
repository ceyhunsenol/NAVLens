use navlens_calendar::ReturnPeriod;
use navlens_core::FundReturnReconciliation;

/// Result of reconciling a published fund return with its observed portfolio contribution.
#[derive(Clone, Debug, PartialEq)]
pub struct FundReturnReconciliationResult {
    period: ReturnPeriod,
    reconciliation: FundReturnReconciliation,
}

impl FundReturnReconciliationResult {
    #[must_use]
    pub(super) const fn new(
        period: ReturnPeriod,
        reconciliation: FundReturnReconciliation,
    ) -> Self {
        Self {
            period,
            reconciliation,
        }
    }

    /// Returns the target return period of the reconciliation.
    #[must_use]
    pub const fn period(&self) -> ReturnPeriod {
        self.period
    }

    /// Returns the canonical core reconciliation result containing the typed subtraction residual.
    #[must_use]
    pub const fn reconciliation(&self) -> FundReturnReconciliation {
        self.reconciliation
    }
}
