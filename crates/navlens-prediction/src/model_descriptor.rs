use crate::{PredictionError, PredictionMetadataField};

/// Identifies the model artifact and the feature definition used by it.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ModelDescriptor {
    name: String,
    version: String,
    feature_set_version: String,
}

impl ModelDescriptor {
    /// Creates validated model provenance metadata.
    ///
    /// # Errors
    /// Returns [`PredictionError`] when a value is blank or contains control
    /// characters.
    pub fn new(
        name: impl Into<String>,
        version: impl Into<String>,
        feature_set_version: impl Into<String>,
    ) -> Result<Self, PredictionError> {
        let name = validate(name.into(), PredictionMetadataField::ModelName)?;
        let version = validate(version.into(), PredictionMetadataField::ModelVersion)?;
        let feature_set_version = validate(
            feature_set_version.into(),
            PredictionMetadataField::FeatureSetVersion,
        )?;

        Ok(Self {
            name,
            version,
            feature_set_version,
        })
    }

    #[must_use]
    pub fn name(&self) -> &str {
        &self.name
    }

    #[must_use]
    pub fn version(&self) -> &str {
        &self.version
    }

    #[must_use]
    pub fn feature_set_version(&self) -> &str {
        &self.feature_set_version
    }
}

fn validate(value: String, field: PredictionMetadataField) -> Result<String, PredictionError> {
    if value.trim().is_empty() {
        return Err(PredictionError::EmptyMetadata(field));
    }
    if value.chars().any(char::is_control) {
        return Err(PredictionError::MetadataContainsControlCharacter(field));
    }

    Ok(value)
}
