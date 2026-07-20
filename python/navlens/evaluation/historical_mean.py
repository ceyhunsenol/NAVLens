"""Historical-mean implementation of the walk-forward estimator boundary."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from navlens import ModelDescriptor
from navlens.datasets.return_series import validated_decimal_returns

from .contracts import FittedPrediction
from .naive_prediction import build_naive_prediction, validate_naive_configuration

MODEL_NAME = "historical-mean-baseline"
FEATURE_SCHEMA_VERSION = "historical-returns-mean-v1"


@dataclass(frozen=True)
class HistoricalMeanBaseline:
    """Predict the expanding historical mean of canonical decimal returns."""

    initial_training_size: int
    model_version: str
    confidence_level: float = 0.90

    def __post_init__(self) -> None:
        validate_naive_configuration(self.initial_training_size, self.confidence_level)

    def fit_predict(self, history: pd.Series) -> FittedPrediction:
        """Predict the historical mean with an absolute-deviation interval."""
        clean_returns = validated_decimal_returns(
            history,
            minimum_size=self.initial_training_size,
        )
        expected_return = float(clean_returns.mean())
        residuals = np.abs(clean_returns.to_numpy() - expected_return)
        model = ModelDescriptor(MODEL_NAME, self.model_version, FEATURE_SCHEMA_VERSION)
        prediction = build_naive_prediction(
            expected_return,
            residuals,
            self.confidence_level,
            model,
        )
        return FittedPrediction(
            prediction=prediction,
            training_start=pd.Timestamp(clean_returns.index[0]),
            training_end=pd.Timestamp(clean_returns.index[-1]),
        )
