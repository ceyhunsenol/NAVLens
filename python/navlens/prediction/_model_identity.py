"""Canonical exact identity mapping for prediction models."""

from navlens import ModelDescriptor

ModelIdentity = tuple[str, str, str]


def model_identity(model: ModelDescriptor) -> ModelIdentity:
    """Return the exact model identity used by grouping and comparison."""
    return model.name, model.version, model.feature_set_version
