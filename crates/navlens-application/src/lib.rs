//! Application use cases and ports for `NAVLens`.

mod error;
mod estimate_portfolio_return;

pub use error::ApplicationError;
pub use estimate_portfolio_return::{
    EstimatePortfolioReturnCommand, EstimatePortfolioReturnResult, WeightedMarketReturnInput,
    estimate_portfolio_return,
};
