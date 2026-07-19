//! Canonical financial types and deterministic calculations for `NAVLens`.

mod decimal_return;
mod error;
mod portfolio;

pub use decimal_return::DecimalReturn;
pub use error::CoreError;
pub use portfolio::{PortfolioComponent, PortfolioEstimate};
