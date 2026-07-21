use crate::CoreError;
use std::fmt::{Display, Formatter};

/// A validated currency code represented as exactly three uppercase ASCII letters.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct CurrencyCode(String);

impl CurrencyCode {
    /// Creates a validated currency code.
    ///
    /// # Errors
    /// Returns an error when the value is not exactly three uppercase ASCII letters.
    pub fn new(value: impl Into<String>) -> Result<Self, CoreError> {
        let value = value.into();
        let bytes = value.as_bytes();
        if bytes.len() != 3 || bytes.iter().any(|&b| !b.is_ascii_uppercase()) {
            return Err(CoreError::InvalidCurrencyCode);
        }
        Ok(Self(value))
    }

    /// Returns the currency code as a string slice.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl AsRef<str> for CurrencyCode {
    fn as_ref(&self) -> &str {
        self.as_str()
    }
}

impl Display for CurrencyCode {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(self.as_str())
    }
}
