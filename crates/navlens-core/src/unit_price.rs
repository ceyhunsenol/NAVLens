use crate::{CoreError, DecimalReturn};

/// A finite, strictly positive published fund unit price.
#[derive(Clone, Copy, Debug, PartialEq, PartialOrd)]
pub struct UnitPrice(f64);

impl UnitPrice {
    /// Creates a validated unit price.
    ///
    /// # Errors
    /// Returns an error when `value` is non-finite, zero, or negative.
    pub fn new(value: f64) -> Result<Self, CoreError> {
        if !value.is_finite() {
            return Err(CoreError::NonFiniteNumber);
        }
        if value <= 0.0 {
            return Err(CoreError::UnitPriceNotPositive(value));
        }
        Ok(Self(value))
    }

    #[must_use]
    pub const fn value(self) -> f64 {
        self.0
    }
}

/// Calculates `(current / previous) - 1` as a decimal return.
///
/// # Errors
/// Returns an error if the finite input prices produce a non-finite result.
pub fn calculate_decimal_return(
    previous: UnitPrice,
    current: UnitPrice,
) -> Result<DecimalReturn, CoreError> {
    DecimalReturn::new((current.value() / previous.value()) - 1.0)
}
