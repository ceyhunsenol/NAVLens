use pyo3::PyErr;
use pyo3::create_exception;
use pyo3::exceptions::PyValueError;
use std::fmt::Display;

create_exception!(
    navlens._native,
    NavlensValidationError,
    PyValueError,
    "Raised when input violates a NAVLens domain invariant."
);

pub(crate) fn validation_error(error: impl Display) -> PyErr {
    NavlensValidationError::new_err(error.to_string())
}
