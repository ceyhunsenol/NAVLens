use crate::CoreError;

/// Probability level associated with a prediction interval.
#[derive(Clone, Copy, Debug, PartialEq, PartialOrd)]
pub struct ConfidenceLevel(f64);

impl ConfidenceLevel {
    /// Creates a confidence level strictly between zero and one.
    ///
    /// # Errors
    /// Returns an error when the value is non-finite or outside `0.0..1.0`.
    pub fn new(value: f64) -> Result<Self, CoreError> {
        if !value.is_finite() {
            return Err(CoreError::NonFiniteNumber);
        }
        if value <= 0.0 || value >= 1.0 {
            return Err(CoreError::ConfidenceLevelOutOfRange(value));
        }

        Ok(Self(value))
    }

    #[must_use]
    pub const fn value(self) -> f64 {
        self.0
    }
}
