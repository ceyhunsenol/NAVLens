"""Linear-baseline implementation of the walk-forward estimator boundary."""

from dataclasses import dataclass

import pandas as pd

from navlens.estimators import predict_next_return
from navlens.training import train_linear_baseline

from .contracts import FittedPrediction


@dataclass(frozen=True)
class LinearBaselineWalkForward:
    """Retrain the linear baseline on each expanding historical window."""

    lookback: int
    model_version: str
    confidence_level: float = 0.90
    minimum_training_returns: int | None = None

    def __post_init__(self) -> None:
        required = self.lookback + 3
        if self.lookback < 1:
            raise ValueError("lookback must be at least one")
        if self.minimum_training_returns is not None:
            if self.minimum_training_returns < required:
                raise ValueError(f"minimum_training_returns must be at least {required}")

    @property
    def initial_training_size(self) -> int:
        return self.minimum_training_returns or self.lookback + 3

    def fit_predict(self, history: pd.Series) -> FittedPrediction:
        """Fit on the supplied history and predict its next return."""
        artifact = train_linear_baseline(
            history,
            lookback=self.lookback,
            model_version=self.model_version,
            confidence_level=self.confidence_level,
        )
        return FittedPrediction(
            prediction=predict_next_return(artifact, history),
            training_start=artifact.training_start,
            training_end=artifact.training_end,
        )
