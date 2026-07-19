use crate::error::validation_error;
use navlens_prediction::ModelDescriptor;
use pyo3::prelude::*;

/// Python projection of validated model provenance metadata.
#[pyclass(
    name = "ModelDescriptor",
    frozen,
    module = "navlens._native",
    from_py_object
)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct PyModelDescriptor {
    inner: ModelDescriptor,
}

impl PyModelDescriptor {
    pub(crate) const fn from_inner(inner: ModelDescriptor) -> Self {
        Self { inner }
    }

    pub(crate) fn into_inner(self) -> ModelDescriptor {
        self.inner
    }
}

#[pymethods]
impl PyModelDescriptor {
    #[new]
    fn new(name: String, version: String, feature_set_version: String) -> PyResult<Self> {
        ModelDescriptor::new(name, version, feature_set_version)
            .map(Self::from_inner)
            .map_err(validation_error)
    }

    #[getter]
    fn name(&self) -> &str {
        self.inner.name()
    }

    #[getter]
    fn version(&self) -> &str {
        self.inner.version()
    }

    #[getter]
    fn feature_set_version(&self) -> &str {
        self.inner.feature_set_version()
    }

    fn __repr__(&self) -> String {
        format!(
            "ModelDescriptor(name='{}', version='{}', feature_set_version='{}')",
            self.inner.name(),
            self.inner.version(),
            self.inner.feature_set_version()
        )
    }
}
