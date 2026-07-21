//! Canonical financial types and deterministic calculations for `NAVLens`.

mod confidence_level;
mod decimal_return;
mod error;
mod expense_rate;
mod fund_id;
mod holding;
mod identifier;
mod portfolio;
mod prediction;
mod unit_price;

pub use confidence_level::ConfidenceLevel;
pub use decimal_return::DecimalReturn;
pub use error::CoreError;
pub use expense_rate::ExpenseRate;
pub use fund_id::FundId;
pub use holding::{AssetClass, HoldingPosition, InstrumentId};
pub use portfolio::{PortfolioComponent, PortfolioEstimate, PortfolioWeight};
pub use prediction::PredictionInterval;
pub use unit_price::{UnitPrice, calculate_decimal_return};
