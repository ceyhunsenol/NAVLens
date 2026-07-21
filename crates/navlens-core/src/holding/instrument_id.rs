use crate::CoreError;
use crate::identifier::{IdentifierError, validate_identifier};
use std::fmt::{Display, Formatter};

/// Stable, provider-neutral identifier of a held instrument.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct InstrumentId(String);

impl InstrumentId {
    pub const MAX_LENGTH: usize = 64;

    /// Creates a normalized instrument identifier.
    ///
    /// Identifiers may contain punctuation but must not contain whitespace or
    /// control characters. A mapper should prefer an ISIN when one exists and
    /// otherwise produce a documented stable identifier.
    ///
    /// # Errors
    /// Returns an error when the identifier is empty, too long, or contains
    /// whitespace or control characters.
    pub fn new(value: impl Into<String>) -> Result<Self, CoreError> {
        let value = value.into();
        validate_identifier(&value, Self::MAX_LENGTH).map_err(map_identifier_error)?;
        Ok(Self(value))
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

fn map_identifier_error(error: IdentifierError) -> CoreError {
    match error {
        IdentifierError::Empty => CoreError::EmptyInstrumentId,
        IdentifierError::TooLong(length) => CoreError::InstrumentIdTooLong(length),
        IdentifierError::ContainsWhitespace => CoreError::InstrumentIdContainsWhitespace,
        IdentifierError::ContainsControlCharacter => {
            CoreError::InstrumentIdContainsControlCharacter
        }
    }
}

impl AsRef<str> for InstrumentId {
    fn as_ref(&self) -> &str {
        self.as_str()
    }
}

impl Display for InstrumentId {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(self.as_str())
    }
}
