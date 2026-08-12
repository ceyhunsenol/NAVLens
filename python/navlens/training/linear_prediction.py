"""Shared fit-and-predict orchestration for the linear return baseline."""

import pandas as pd

from navlens.estimators import FittedPrediction, predict_next_return

from .linear_baseline import train_linear_baseline


def fit_predict_linear_baseline(
    returns: pd.Series,
    *,
    lookback: int,
    model_version: str,
    confidence_level: float = 0.90,
) -> FittedPrediction:
    """Train the linear baseline and predict the return following its history."""
    artifact = train_linear_baseline(
        returns,
        lookback=lookback,
        model_version=model_version,
        confidence_level=confidence_level,
    )
    return FittedPrediction(
        prediction=predict_next_return(artifact, returns),
        training_start=artifact.training_start,
        training_end=artifact.training_end,
    )
