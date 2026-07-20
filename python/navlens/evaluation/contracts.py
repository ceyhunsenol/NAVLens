"""Estimator boundary consumed by walk-forward evaluation."""

from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from navlens import ReturnPrediction


@dataclass(frozen=True)
class FittedPrediction:
    """One prediction together with the training window that produced it."""

    prediction: ReturnPrediction
    training_start: pd.Timestamp
    training_end: pd.Timestamp


class WalkForwardEstimator(Protocol):
    """Model lifecycle required by the model-independent evaluation engine."""

    @property
    def initial_training_size(self) -> int: ...

    def fit_predict(self, history: pd.Series) -> FittedPrediction: ...
