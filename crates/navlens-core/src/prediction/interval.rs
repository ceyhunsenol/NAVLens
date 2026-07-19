use crate::{ConfidenceLevel, CoreError, DecimalReturn};

/// Inclusive lower and upper return bounds at a stated confidence level.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PredictionInterval {
    lower: DecimalReturn,
    upper: DecimalReturn,
    confidence_level: ConfidenceLevel,
}

impl PredictionInterval {
    /// Creates an inclusive prediction interval.
    ///
    /// # Errors
    /// Returns an error when the lower bound is greater than the upper bound.
    pub fn new(
        lower: DecimalReturn,
        upper: DecimalReturn,
        confidence_level: ConfidenceLevel,
    ) -> Result<Self, CoreError> {
        if lower > upper {
            return Err(CoreError::PredictionIntervalBounds {
                lower: lower.value(),
                upper: upper.value(),
            });
        }

        Ok(Self {
            lower,
            upper,
            confidence_level,
        })
    }

    #[must_use]
    pub const fn lower(self) -> DecimalReturn {
        self.lower
    }

    #[must_use]
    pub const fn upper(self) -> DecimalReturn {
        self.upper
    }

    #[must_use]
    pub const fn confidence_level(self) -> ConfidenceLevel {
        self.confidence_level
    }

    #[must_use]
    pub fn contains(self, value: DecimalReturn) -> bool {
        value >= self.lower && value <= self.upper
    }

    #[must_use]
    pub fn width(self) -> f64 {
        self.upper.value() - self.lower.value()
    }
}
