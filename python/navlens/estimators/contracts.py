"""Model-independent contracts shared by training and evaluation workflows."""

from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from navlens import ReturnPrediction


@dataclass(frozen=True, slots=True)
class FittedPrediction:
    """One prediction together with the history window that produced it."""

    prediction: ReturnPrediction
    training_start: pd.Timestamp
    training_end: pd.Timestamp


class NextReturnEstimator(Protocol):
    """Lifecycle required from an expanding-history return estimator."""

    @property
    def initial_training_size(self) -> int: ...

    def fit_predict(self, history: pd.Series) -> FittedPrediction: ...
