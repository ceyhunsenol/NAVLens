"""Linear-baseline implementation of the walk-forward estimator boundary."""

from dataclasses import dataclass

import pandas as pd

from navlens.estimators import LinearBaselineConfig
from navlens.training import fit_predict_linear_baseline

from .contracts import FittedPrediction


@dataclass(frozen=True)
class LinearBaselineWalkForward:
    """Retrain the linear baseline on each expanding historical window."""

    lookback: int
    model_version: str
    confidence_level: float = 0.90
    minimum_training_returns: int | None = None

    def __post_init__(self) -> None:
        config = LinearBaselineConfig(
            lookback=self.lookback,
            minimum_training_returns=self.minimum_training_returns,
        )
        object.__setattr__(self, "_config", config)

    @property
    def initial_training_size(self) -> int:
        return self._config.resolved_minimum_training_returns

    def fit_predict(self, history: pd.Series) -> FittedPrediction:
        """Fit on the supplied history and predict its next return."""
        return fit_predict_linear_baseline(
            history,
            lookback=self.lookback,
            model_version=self.model_version,
            confidence_level=self.confidence_level,
        )
