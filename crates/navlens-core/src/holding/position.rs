use super::{AssetClass, InstrumentId};
use crate::PortfolioWeight;

/// One instrument exposure in a fund composition snapshot.
#[derive(Clone, Debug, PartialEq)]
pub struct HoldingPosition {
    instrument_id: InstrumentId,
    asset_class: AssetClass,
    fund_total_weight: PortfolioWeight,
}

impl HoldingPosition {
    #[must_use]
    pub const fn new(
        instrument_id: InstrumentId,
        asset_class: AssetClass,
        fund_total_weight: PortfolioWeight,
    ) -> Self {
        Self {
            instrument_id,
            asset_class,
            fund_total_weight,
        }
    }

    #[must_use]
    pub const fn instrument_id(&self) -> &InstrumentId {
        &self.instrument_id
    }

    #[must_use]
    pub const fn asset_class(&self) -> AssetClass {
        self.asset_class
    }

    /// Returns the instrument value divided by fund total value.
    #[must_use]
    pub const fn fund_total_weight(&self) -> PortfolioWeight {
        self.fund_total_weight
    }
}
