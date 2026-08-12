"""Explicit, reproducible estimator-training workflows."""

from .linear_baseline import train_linear_baseline
from .linear_prediction import fit_predict_linear_baseline

__all__ = ["fit_predict_linear_baseline", "train_linear_baseline"]
