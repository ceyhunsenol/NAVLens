use crate::CoreError;

/// A decimal expense rate where `0.01` represents one percent.
#[derive(Clone, Copy, Debug, Default, PartialEq, PartialOrd)]
pub struct ExpenseRate(f64);

impl ExpenseRate {
    /// Creates an expense rate in the inclusive range `0.0..=1.0`.
    ///
    /// # Errors
    /// Returns an error when the value is non-finite or outside the valid range.
    pub fn new(value: f64) -> Result<Self, CoreError> {
        if !value.is_finite() {
            return Err(CoreError::NonFiniteNumber);
        }
        if !(0.0..=1.0).contains(&value) {
            return Err(CoreError::ExpenseRateOutOfRange(value));
        }

        Ok(Self(value))
    }

    #[must_use]
    pub const fn value(self) -> f64 {
        self.0
    }
}
