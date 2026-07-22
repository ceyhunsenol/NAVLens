//! Contracts for aligning holdings and prices capability.

mod candidate;
mod error;
mod gap;
mod policy;

pub use candidate::SecurityPriceHistoryCandidate;
pub use error::AlignmentContractError;
pub use gap::CoverageGapReason;
pub use policy::AlignmentPolicy;
