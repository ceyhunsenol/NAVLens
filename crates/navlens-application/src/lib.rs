//! Application use cases and ports for `NAVLens`.

mod align_holdings_prices;
mod error;
mod estimate_portfolio_return;

pub use align_holdings_prices::{
    AlignmentContractError, AlignmentPolicy, CoverageGapReason, SecurityPriceHistoryCandidate,
};
pub use error::ApplicationError;
pub use estimate_portfolio_return::{
    EstimatePortfolioReturnCommand, EstimatePortfolioReturnResult, WeightedMarketReturnInput,
    estimate_portfolio_return,
};
