use navlens_calendar::{MarketDate, PriceAdjustment};
use navlens_core::{AssetClass, CurrencyCode};

/// Reasons why a security price history may fail to cover alignment requirements.
#[derive(Clone, Debug, PartialEq)]
pub enum CoverageGapReason {
    /// The holding's asset class is not supported by the initial matcher.
    UnsupportedAssetClass {
        /// Unsupported canonical asset class.
        asset_class: AssetClass,
    },
    /// No price history was found.
    MissingPriceSeries,
    /// Insufficient number of observations found vs required.
    InsufficientObservations {
        /// Number of observations found.
        found: usize,
        /// Number of observations required.
        required: usize,
    },
    /// The currency of the observations does not match the expected currency.
    CurrencyMismatch {
        /// The expected currency code.
        expected: CurrencyCode,
        /// The found currency code.
        found: CurrencyCode,
    },
    /// The price adjustment of the observations does not match the expected adjustment.
    IncompatiblePriceAdjustment {
        /// The expected price adjustment.
        expected: PriceAdjustment,
        /// The found price adjustment.
        found: PriceAdjustment,
    },
    /// The latest eligible observation is too old for the explicit policy.
    StalePrices {
        /// Date of the latest eligible observation.
        latest_observation_date: MarketDate,
        /// Pricing date against which staleness is evaluated.
        pricing_as_of_date: MarketDate,
        /// Maximum permitted distance in whole calendar days.
        max_staleness_calendar_days: u32,
    },
}
