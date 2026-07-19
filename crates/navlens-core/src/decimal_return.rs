use crate::CoreError;

/// A decimal return where `0.01` represents one percent.
#[derive(Clone, Copy, Debug, Default, PartialEq, PartialOrd)]
pub struct DecimalReturn(f64);

impl DecimalReturn {
    /// Creates a finite decimal return.
    ///
    /// # Errors
    /// Returns [`CoreError::NonFiniteNumber`] for NaN or infinity.
    pub fn new(value: f64) -> Result<Self, CoreError> {
        if value.is_finite() {
            Ok(Self(value))
        } else {
            Err(CoreError::NonFiniteNumber)
        }
    }

    #[must_use]
    pub const fn value(self) -> f64 {
        self.0
    }
}
