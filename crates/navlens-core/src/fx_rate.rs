use crate::CoreError;

/// A finite, strictly positive foreign exchange rate value representing quote units per one base unit.
#[derive(Clone, Copy, Debug, PartialEq, PartialOrd)]
pub struct FxRate(f64);

impl FxRate {
    /// Creates a validated foreign exchange rate.
    ///
    /// # Errors
    /// Returns an error when `quote_currency_per_one_base_currency` is non-finite, zero, or negative.
    pub fn new(quote_currency_per_one_base_currency: f64) -> Result<Self, CoreError> {
        if !quote_currency_per_one_base_currency.is_finite() {
            return Err(CoreError::NonFiniteNumber);
        }
        if quote_currency_per_one_base_currency <= 0.0 {
            return Err(CoreError::FxRateNotPositive(
                quote_currency_per_one_base_currency,
            ));
        }
        Ok(Self(quote_currency_per_one_base_currency))
    }

    /// Returns the rate scalar as quote currency units per one base currency unit.
    #[must_use]
    pub const fn quote_currency_per_one_base_currency(self) -> f64 {
        self.0
    }
}
