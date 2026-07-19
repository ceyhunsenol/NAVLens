use crate::CoreError;

/// Share of a portfolio where `1.0` represents the entire portfolio.
#[derive(Clone, Copy, Debug, Default, PartialEq, PartialOrd)]
pub struct PortfolioWeight(f64);

impl PortfolioWeight {
    /// Creates a portfolio weight in the inclusive range `0.0..=1.0`.
    ///
    /// # Errors
    /// Returns an error when the value is non-finite or outside the valid range.
    pub fn new(value: f64) -> Result<Self, CoreError> {
        if !value.is_finite() {
            return Err(CoreError::NonFiniteNumber);
        }
        if !(0.0..=1.0).contains(&value) {
            return Err(CoreError::PortfolioWeightOutOfRange(value));
        }

        Ok(Self(value))
    }

    #[must_use]
    pub const fn value(self) -> f64 {
        self.0
    }
}
