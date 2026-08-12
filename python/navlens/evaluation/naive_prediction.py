"""Compatibility exports for canonical naive-estimator mechanics."""

from navlens.estimators.naive_prediction import (
    build_naive_prediction,
    validate_naive_configuration,
)

__all__ = ["build_naive_prediction", "validate_naive_configuration"]
