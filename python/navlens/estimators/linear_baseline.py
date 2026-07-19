"""Deterministic linear-regression baseline and its auditable metadata."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

from navlens import ModelDescriptor, ReturnPrediction, create_return_prediction
from navlens.features import LaggedReturnDataset, build_latest_feature_row

MODEL_NAME = "linear-regression-baseline"


@dataclass(frozen=True)
class LinearBaselineArtifact:
    """A fitted estimator plus the metadata required to reproduce its contract."""

    estimator: LinearRegression
    feature_names: tuple[str, ...]
    feature_schema_version: str
    target_definition: str
    model_version: str
    training_start: pd.Timestamp
    training_end: pd.Timestamp
    confidence_level: float
    residual_radius: float
    evaluation_metrics: Mapping[str, float]

    @property
    def lookback(self) -> int:
        return len(self.feature_names)


def fit_linear_baseline(
    dataset: LaggedReturnDataset,
    *,
    model_version: str,
    confidence_level: float = 0.90,
) -> LinearBaselineArtifact:
    """Fit a deterministic baseline and calibrate a training-residual interval."""
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be between zero and one")
    if len(dataset.targets) < 3:
        raise ValueError("at least three training rows are required")

    estimator = LinearRegression().fit(dataset.features, dataset.targets)
    fitted = estimator.predict(dataset.features)
    residuals = np.abs(dataset.targets.to_numpy() - fitted)
    residual_radius = float(np.quantile(residuals, confidence_level, method="higher"))
    return LinearBaselineArtifact(
        estimator=estimator,
        feature_names=tuple(dataset.features.columns),
        feature_schema_version=dataset.feature_schema_version,
        target_definition=dataset.target_definition,
        model_version=model_version,
        training_start=pd.Timestamp(dataset.targets.index[0]),
        training_end=pd.Timestamp(dataset.targets.index[-1]),
        confidence_level=confidence_level,
        residual_radius=residual_radius,
        evaluation_metrics=_evaluation_metrics(dataset, fitted),
    )


def predict_next_return(
    artifact: LinearBaselineArtifact,
    returns: pd.Series,
) -> ReturnPrediction:
    """Predict the next decimal return and validate it through the Rust contract."""
    features = build_latest_feature_row(returns, lookback=artifact.lookback)
    if tuple(features.columns) != artifact.feature_names:
        raise ValueError("feature schema does not match the fitted artifact")

    expected_return = float(artifact.estimator.predict(features)[0])
    model = ModelDescriptor(
        MODEL_NAME,
        artifact.model_version,
        artifact.feature_schema_version,
    )
    return create_return_prediction(
        expected_return,
        expected_return - artifact.residual_radius,
        expected_return + artifact.residual_radius,
        artifact.confidence_level,
        model,
    )


def _evaluation_metrics(
    dataset: LaggedReturnDataset,
    linear_fitted: np.ndarray,
) -> Mapping[str, float]:
    dummy = DummyRegressor(strategy="mean").fit(dataset.features, dataset.targets)
    dummy_fitted = dummy.predict(dataset.features)
    return MappingProxyType(
        {
            "linear_train_mae": float(mean_absolute_error(dataset.targets, linear_fitted)),
            "linear_train_rmse": _rmse(dataset.targets, linear_fitted),
            "mean_dummy_train_mae": float(mean_absolute_error(dataset.targets, dummy_fitted)),
            "mean_dummy_train_rmse": _rmse(dataset.targets, dummy_fitted),
        }
    )


def _rmse(targets: pd.Series, fitted: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(targets, fitted)))
