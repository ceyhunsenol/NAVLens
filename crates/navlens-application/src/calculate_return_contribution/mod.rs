mod aggregate;
mod breakdown;
mod calculate;
mod component;
mod contribution;
mod error;
mod exact_period;
mod gap;
mod result;

pub use calculate::calculate_return_contribution;
pub use component::ComponentContribution;
pub use error::CalculateReturnContributionError;
pub use gap::{ReturnCoverageGap, ReturnCoverageGapReason};
pub use result::ReturnContributionResult;

pub(crate) use aggregate::calculate_aggregate_contribution;
pub(crate) use breakdown::construct_return_coverage_breakdown;
pub(crate) use contribution::calculate_canonical_contribution;
pub(crate) use exact_period::match_exact_period_return;
