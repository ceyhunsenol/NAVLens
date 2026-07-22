use crate::align_holdings_prices::{AlignmentPolicy, CoverageGapReason};
use navlens_calendar::SecurityPriceSeries;
use navlens_core::{HoldingPosition, PortfolioCoverageWeights};

/// A holding position paired with its accepted security price series.
#[derive(Clone, Debug, PartialEq)]
pub struct CoveredHoldingPrice {
    holding: HoldingPosition,
    series: SecurityPriceSeries,
}

impl CoveredHoldingPrice {
    /// Creates a new `CoveredHoldingPrice`.
    #[must_use]
    pub(crate) const fn new(holding: HoldingPosition, series: SecurityPriceSeries) -> Self {
        Self { holding, series }
    }

    /// Returns the holding position.
    #[must_use]
    pub const fn holding(&self) -> &HoldingPosition {
        &self.holding
    }

    /// Returns the matched security price series.
    #[must_use]
    pub const fn series(&self) -> &SecurityPriceSeries {
        &self.series
    }
}

/// A listed holding position that failed to align with an accepted price series.
#[derive(Clone, Debug, PartialEq)]
pub struct UncoveredHolding {
    holding: HoldingPosition,
    reason: CoverageGapReason,
}

impl UncoveredHolding {
    /// Creates a new `UncoveredHolding`.
    #[must_use]
    pub(crate) const fn new(holding: HoldingPosition, reason: CoverageGapReason) -> Self {
        Self { holding, reason }
    }

    /// Returns the holding position.
    #[must_use]
    pub const fn holding(&self) -> &HoldingPosition {
        &self.holding
    }

    /// Returns the reason why this holding is uncovered.
    #[must_use]
    pub const fn reason(&self) -> &CoverageGapReason {
        &self.reason
    }
}

/// The result of aligning holdings to security prices.
#[derive(Clone, Debug, PartialEq)]
pub struct PortfolioCoverageReport {
    covered: Vec<CoveredHoldingPrice>,
    uncovered_listed: Vec<UncoveredHolding>,
    weights: PortfolioCoverageWeights,
    policy: AlignmentPolicy,
}

impl PortfolioCoverageReport {
    /// Creates a new `PortfolioCoverageReport`.
    #[must_use]
    pub(crate) const fn new(
        covered: Vec<CoveredHoldingPrice>,
        uncovered_listed: Vec<UncoveredHolding>,
        weights: PortfolioCoverageWeights,
        policy: AlignmentPolicy,
    ) -> Self {
        Self {
            covered,
            uncovered_listed,
            weights,
            policy,
        }
    }

    /// Returns the covered holding prices.
    #[must_use]
    pub fn covered(&self) -> &[CoveredHoldingPrice] {
        &self.covered
    }

    /// Returns the uncovered listed holdings.
    #[must_use]
    pub fn uncovered_listed(&self) -> &[UncoveredHolding] {
        &self.uncovered_listed
    }

    /// Returns the coverage accounting weights.
    #[must_use]
    pub const fn weights(&self) -> &PortfolioCoverageWeights {
        &self.weights
    }

    /// Returns the alignment policy used to construct this report.
    #[must_use]
    pub const fn policy(&self) -> &AlignmentPolicy {
        &self.policy
    }
}
