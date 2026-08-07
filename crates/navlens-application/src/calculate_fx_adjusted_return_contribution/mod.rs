mod boundary;
mod calculate;
mod candidates;
mod error;
mod evidence;
mod policy;
mod result;

pub use calculate::calculate_fx_adjusted_return_contribution;
pub use error::FxReturnContractError;
pub use evidence::{CurrencyReturnAdjustment, FxAdjustmentEvidence, FxBoundaryEvidence};
pub use policy::FxReturnPolicy;
pub use result::{FxAdjustedComponentContribution, FxAdjustedReturnContributionResult};
