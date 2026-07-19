mod command;
mod execute;
mod result;

pub use command::{EstimatePortfolioReturnCommand, WeightedMarketReturnInput};
pub use execute::estimate_portfolio_return;
pub use result::EstimatePortfolioReturnResult;
