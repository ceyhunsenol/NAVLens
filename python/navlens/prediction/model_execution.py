"""Model selection and execution for one point-in-time return history."""

from dataclasses import dataclass

import pandas as pd

from navlens.estimators import (
    FittedPrediction,
    HistoricalMeanBaseline,
    LastReturnBaseline,
    LinearBaselineConfig,
)
from navlens.training import fit_predict_linear_baseline

from .options import PredictionModelKind


@dataclass(frozen=True, slots=True)
class PredictionModelFit:
    """A fitted prediction with its effective history configuration."""

    fitted: FittedPrediction
    required_training_returns: int
    effective_lookback: int


def fit_prediction_model(
    returns: pd.Series,
    *,
    model_kind: PredictionModelKind,
    lookback: int,
    minimum_training_returns: int | None,
    model_version: str,
    confidence_level: float,
) -> PredictionModelFit:
    """Fit and execute one selected estimator without duplicating its formula."""
    required = resolve_required_training_returns(model_kind, lookback, minimum_training_returns)
    if model_kind is PredictionModelKind.LINEAR:
        return _fit_linear(returns, lookback, required, model_version, confidence_level)
    estimator = _naive_estimator(model_kind, required, model_version, confidence_level)
    fitted = estimator.fit_predict(returns)
    effective_lookback = 1 if model_kind is PredictionModelKind.LAST_RETURN else len(returns)
    return PredictionModelFit(fitted, required, effective_lookback)


def resolve_required_training_returns(
    model_kind: PredictionModelKind,
    lookback: int,
    minimum_training_returns: int | None,
) -> int:
    """Resolve the visible-history threshold for the selected estimator."""
    if not isinstance(model_kind, PredictionModelKind):
        raise ValueError("model_kind must be a PredictionModelKind instance")
    if model_kind is PredictionModelKind.LINEAR:
        config = LinearBaselineConfig(lookback, minimum_training_returns)
        return config.resolved_minimum_training_returns
    required = 3 if minimum_training_returns is None else minimum_training_returns
    if isinstance(required, bool) or not isinstance(required, int) or required < 3:
        raise ValueError("minimum_training_returns must be at least three")
    return required


def _fit_linear(
    returns: pd.Series,
    lookback: int,
    required_training_returns: int,
    model_version: str,
    confidence_level: float,
) -> PredictionModelFit:
    fitted = fit_predict_linear_baseline(
        returns,
        lookback=lookback,
        model_version=model_version,
        confidence_level=confidence_level,
    )
    return PredictionModelFit(fitted, required_training_returns, lookback)


def _naive_estimator(
    model_kind: PredictionModelKind,
    required: int,
    model_version: str,
    confidence_level: float,
) -> HistoricalMeanBaseline | LastReturnBaseline:
    estimator_type = (
        LastReturnBaseline
        if model_kind is PredictionModelKind.LAST_RETURN
        else HistoricalMeanBaseline
    )
    return estimator_type(required, model_version, confidence_level)
