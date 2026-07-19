"""Training orchestration for the first NAVLens baseline estimator."""

import pandas as pd

from navlens.estimators import LinearBaselineArtifact, fit_linear_baseline
from navlens.features import build_lagged_return_dataset


def train_linear_baseline(
    returns: pd.Series,
    *,
    lookback: int,
    model_version: str,
    confidence_level: float = 0.90,
) -> LinearBaselineArtifact:
    """Create the feature dataset and fit one versioned baseline artifact."""
    dataset = build_lagged_return_dataset(returns, lookback=lookback)
    return fit_linear_baseline(
        dataset,
        model_version=model_version,
        confidence_level=confidence_level,
    )
