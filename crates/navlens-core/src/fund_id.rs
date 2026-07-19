use crate::CoreError;
use std::fmt::{Display, Formatter};

/// Stable provider-facing identifier of an investment fund.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct FundId(String);

impl FundId {
    pub const MAX_LENGTH: usize = 64;

    /// Creates a validated fund identifier.
    ///
    /// # Errors
    /// Returns an error when the identifier is empty, too long, or contains
    /// whitespace or control characters.
    pub fn new(value: impl Into<String>) -> Result<Self, CoreError> {
        let value = value.into();
        let length = value.chars().count();

        if value.is_empty() {
            return Err(CoreError::EmptyFundId);
        }
        if length > Self::MAX_LENGTH {
            return Err(CoreError::FundIdTooLong(length));
        }
        if value.chars().any(char::is_whitespace) {
            return Err(CoreError::FundIdContainsWhitespace);
        }
        if value.chars().any(char::is_control) {
            return Err(CoreError::FundIdContainsControlCharacter);
        }

        Ok(Self(value))
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl AsRef<str> for FundId {
    fn as_ref(&self) -> &str {
        self.as_str()
    }
}

impl Display for FundId {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(self.as_str())
    }
}
