#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum IdentifierError {
    Empty,
    TooLong(usize),
    ContainsWhitespace,
    ContainsControlCharacter,
}

pub(crate) fn validate_identifier(value: &str, max_length: usize) -> Result<(), IdentifierError> {
    let length = value.chars().count();

    if value.is_empty() {
        return Err(IdentifierError::Empty);
    }
    if length > max_length {
        return Err(IdentifierError::TooLong(length));
    }
    if value.chars().any(char::is_whitespace) {
        return Err(IdentifierError::ContainsWhitespace);
    }
    if value.chars().any(char::is_control) {
        return Err(IdentifierError::ContainsControlCharacter);
    }

    Ok(())
}
