//! Application use cases and ports for `NAVLens`.

mod align_holdings_prices;
mod calculate_return_contribution;
mod error;
mod estimate_portfolio_return;

pub use align_holdings_prices::{
    AlignHoldingsPricesError, AlignmentContractError, AlignmentPolicy, CoverageGapReason,
    CoveredHoldingPrice, PortfolioCoverageReport, SecurityPriceHistoryCandidate, UncoveredHolding,
    align_holdings_prices,
};
pub use calculate_return_contribution::{
    CalculateReturnContributionError, ComponentContribution, ReturnContributionResult,
    ReturnCoverageGap, ReturnCoverageGapReason, calculate_return_contribution,
};
pub use error::ApplicationError;
pub use estimate_portfolio_return::{
    EstimatePortfolioReturnCommand, EstimatePortfolioReturnResult, WeightedMarketReturnInput,
    estimate_portfolio_return,
};
