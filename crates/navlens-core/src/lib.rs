//! Canonical financial types and deterministic calculations for `NAVLens`.

mod confidence_level;
mod currency_code;
mod currency_pair;
mod decimal_return;
mod error;
mod expense_rate;
mod fund_id;
mod fx_rate;
mod fx_rate_kind;
mod holding;
mod identifier;
mod portfolio;
mod prediction;
mod unit_price;

pub use confidence_level::ConfidenceLevel;
pub use currency_code::CurrencyCode;
pub use currency_pair::CurrencyPair;
pub use decimal_return::DecimalReturn;
pub use error::CoreError;
pub use expense_rate::ExpenseRate;
pub use fund_id::FundId;
pub use fx_rate::FxRate;
pub use fx_rate_kind::FxRateKind;
pub use holding::{AssetClass, HoldingPosition, InstrumentId};
pub use portfolio::{
    FundReturnReconciliation, PortfolioComponent, PortfolioComponentContribution,
    PortfolioCoverageWeights, PortfolioEstimate, PortfolioReturnContribution, PortfolioWeight,
};
pub use prediction::PredictionInterval;
pub use unit_price::{UnitPrice, calculate_decimal_return};
