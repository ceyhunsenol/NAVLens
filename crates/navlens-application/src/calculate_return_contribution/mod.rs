mod calculate;
mod component;
mod error;
mod gap;
mod result;

pub use calculate::calculate_return_contribution;
pub use component::ComponentContribution;
pub use error::CalculateReturnContributionError;
pub use gap::{ReturnCoverageGap, ReturnCoverageGapReason};
pub use result::ReturnContributionResult;
