//! Contracts for aligning holdings and prices capability.

mod candidate;
mod error;
mod gap;
mod matcher;
mod policy;
mod report;

pub use candidate::SecurityPriceHistoryCandidate;
pub use error::{AlignHoldingsPricesError, AlignmentContractError};
pub use gap::CoverageGapReason;
pub use matcher::align_holdings_prices;
pub use policy::AlignmentPolicy;
pub use report::{CoveredHoldingPrice, PortfolioCoverageReport, UncoveredHolding};
