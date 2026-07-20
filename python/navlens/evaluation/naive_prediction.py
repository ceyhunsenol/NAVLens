"""Shared prediction mechanics for transparent naive baselines."""

import numpy as np

from navlens import ModelDescriptor, ReturnPrediction, create_return_prediction


def validate_naive_configuration(
    initial_training_size: int,
    confidence_level: float,
) -> None:
    """Validate the common configuration required by naive baselines."""
    if initial_training_size < 3:
        raise ValueError("initial_training_size must be at least three")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be between zero and one")


def build_naive_prediction(
    expected_return: float,
    absolute_residuals: np.ndarray,
    confidence_level: float,
    model: ModelDescriptor,
) -> ReturnPrediction:
    """Build a Rust-validated prediction from one transparent residual rule."""
    residual_radius = float(np.quantile(absolute_residuals, confidence_level, method="higher"))
    return create_return_prediction(
        expected_return,
        expected_return - residual_radius,
        expected_return + residual_radius,
        confidence_level,
        model,
    )
