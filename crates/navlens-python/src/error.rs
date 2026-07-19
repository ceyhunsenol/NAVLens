use navlens_application::ApplicationError;
use pyo3::PyErr;
use pyo3::create_exception;
use pyo3::exceptions::PyValueError;

create_exception!(
    navlens._native,
    NavlensValidationError,
    PyValueError,
    "Raised when input violates a NAVLens domain invariant."
);

pub(crate) fn application_error(error: ApplicationError) -> PyErr {
    NavlensValidationError::new_err(error.to_string())
}
