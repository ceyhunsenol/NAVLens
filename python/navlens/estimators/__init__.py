"""Statistical estimators owned by the Python research layer."""

from .linear_baseline import (
    LinearBaselineArtifact,
    fit_linear_baseline,
    predict_next_return,
)

__all__ = [
    "LinearBaselineArtifact",
    "fit_linear_baseline",
    "predict_next_return",
]
