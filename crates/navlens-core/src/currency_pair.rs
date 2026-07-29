use crate::{CoreError, CurrencyCode};

/// A validated directional currency pair consisting of distinct base and quote currencies.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct CurrencyPair {
    base_currency: CurrencyCode,
    quote_currency: CurrencyCode,
}

impl CurrencyPair {
    /// Creates a validated currency pair.
    ///
    /// # Errors
    /// Returns an error when `base_currency` and `quote_currency` are identical.
    pub fn new(
        base_currency: CurrencyCode,
        quote_currency: CurrencyCode,
    ) -> Result<Self, CoreError> {
        if base_currency == quote_currency {
            return Err(CoreError::IdenticalCurrencyPair);
        }
        Ok(Self {
            base_currency,
            quote_currency,
        })
    }

    /// Returns the base currency of the pair.
    #[must_use]
    pub const fn base_currency(&self) -> &CurrencyCode {
        &self.base_currency
    }

    /// Returns the quote currency of the pair.
    #[must_use]
    pub const fn quote_currency(&self) -> &CurrencyCode {
        &self.quote_currency
    }
}
